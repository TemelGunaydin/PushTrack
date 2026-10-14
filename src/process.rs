//! File-backed, cancellable owned process groups shared by Git and local inference.
use anyhow::{Context, Result, bail};
use nix::{
    sys::signal::{Signal, killpg},
    unistd::Pid,
};
use std::{
    fs::File,
    io::{Read, Seek, SeekFrom, Write},
    os::unix::process::CommandExt,
    process::{Child, Command, ExitStatus, Stdio},
    sync::atomic::{AtomicBool, Ordering},
    thread,
    time::{Duration, Instant},
};

pub struct Output {
    pub status: ExitStatus,
    pub stdout: Vec<u8>,
    pub stderr: String,
}

struct RunningChild {
    child: Child,
    active: bool,
}
impl RunningChild {
    fn stop(&mut self) {
        let group = Pid::from_raw(self.child.id() as i32);
        let _ = killpg(group, Signal::SIGTERM);
        thread::sleep(Duration::from_millis(50));
        let _ = killpg(group, Signal::SIGKILL);
        let _ = self.child.wait();
        self.active = false;
    }
}
impl Drop for RunningChild {
    fn drop(&mut self) {
        if self.active {
            self.stop();
        }
    }
}

pub(crate) fn run(
    command: Command,
    input: Option<&[u8]>,
    cancel: &AtomicBool,
    timeout: Duration,
    cap: Option<u64>,
    label: &str,
) -> Result<Output> {
    run_observed(command, input, cancel, (timeout, cap), label, || Ok(()))
}

pub(crate) fn run_observed(
    mut command: Command,
    input: Option<&[u8]>,
    cancel: &AtomicBool,
    limits: (Duration, Option<u64>),
    label: &str,
    mut observe: impl FnMut() -> Result<()>,
) -> Result<Output> {
    let (timeout, cap) = limits;
    if cancel.load(Ordering::Relaxed) {
        bail!("Cancelled");
    }
    let mut stdout = tempfile::tempfile()?;
    let mut stderr = tempfile::tempfile()?;
    let stdin = if let Some(bytes) = input {
        let mut file = tempfile::tempfile()?;
        file.write_all(bytes)?;
        file.seek(SeekFrom::Start(0))?;
        Stdio::from(file)
    } else {
        Stdio::null()
    };
    command
        .stdin(stdin)
        .stdout(stdout.try_clone()?)
        .stderr(stderr.try_clone()?)
        .process_group(0);
    let child = command
        .spawn()
        .with_context(|| format!("Could not start {label}"))?;
    let mut running = RunningChild {
        child,
        active: true,
    };
    let start = Instant::now();
    let status = loop {
        observe()?;
        // Check limits before accepting an already-exited child's output, too.
        if let Some(cap) = cap
            && (stdout.metadata()?.len() > cap || stderr.metadata()?.len() > cap)
        {
            bail!("{label} output exceeded the limit; no truncation allowed");
        }
        if let Some(status) = running.child.try_wait()? {
            // A crashed connector must not leave its model server (or other helpers) alive.
            let _ = killpg(Pid::from_raw(running.child.id() as i32), Signal::SIGKILL);
            running.active = false;
            break status;
        }
        if cancel.load(Ordering::Relaxed) {
            bail!("Cancelled");
        }
        if start.elapsed() >= timeout {
            bail!("{label} timed out after {} seconds", timeout.as_secs());
        }
        thread::sleep(Duration::from_millis(5));
    };
    if let Some(cap) = cap
        && (stdout.metadata()?.len() > cap || stderr.metadata()?.len() > cap)
    {
        bail!("{label} output exceeded the limit; no truncation allowed");
    }
    Ok(Output {
        status,
        stdout: read(&mut stdout)?,
        stderr: String::from_utf8_lossy(&read(&mut stderr)?).into_owned(),
    })
}
fn read(file: &mut File) -> Result<Vec<u8>> {
    file.seek(SeekFrom::Start(0))?;
    let mut bytes = Vec::new();
    file.read_to_end(&mut bytes)?;
    Ok(bytes)
}
