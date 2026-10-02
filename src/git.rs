use crate::model::{Report, Snapshot, Verification};
use anyhow::{Context, Result, bail};
use nix::{
    sys::signal::{Signal, killpg},
    unistd::Pid,
};
use std::{
    fs::File,
    io::{Read, Seek, SeekFrom},
    os::unix::process::CommandExt,
    path::Path,
    process::{Child, Command, ExitStatus, Stdio},
    sync::{
        Arc,
        atomic::{AtomicBool, Ordering},
    },
    thread,
    time::{Duration, Instant, SystemTime},
};

#[derive(Clone)]
pub struct Git {
    pub cancel: Arc<AtomicBool>,
    pub timeout: Duration,
}

pub struct Output {
    pub status: ExitStatus,
    pub stdout: Vec<u8>,
    pub stderr: String,
}

impl Default for Git {
    fn default() -> Self {
        Self {
            cancel: Arc::new(AtomicBool::new(false)),
            timeout: Duration::from_secs(20),
        }
    }
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

impl Git {
    pub fn run(&self, path: &Path, args: &[&str]) -> Result<Output> {
        if self.cancel.load(Ordering::Relaxed) {
            bail!("Cancelled");
        }
        let mut stdout = tempfile::tempfile()?;
        let mut stderr = tempfile::tempfile()?;
        let mut command = Command::new("git");
        command
            .args(["-c", "core.fsmonitor=false", "-c", "color.ui=false"])
            .args(args)
            .current_dir(path)
            .stdin(Stdio::null())
            .stdout(stdout.try_clone()?)
            .stderr(stderr.try_clone()?)
            .process_group(0)
            .env("LC_ALL", "C")
            .env("GIT_OPTIONAL_LOCKS", "0")
            .env("GIT_TERMINAL_PROMPT", "0")
            .env("GCM_INTERACTIVE", "never")
            .env("GIT_ASKPASS", "/usr/bin/false")
            .env("SSH_ASKPASS", "/usr/bin/false")
            .env("SSH_ASKPASS_REQUIRE", "force");
        for key in [
            "GIT_DIR",
            "GIT_WORK_TREE",
            "GIT_INDEX_FILE",
            "GIT_COMMON_DIR",
            "GIT_OBJECT_DIRECTORY",
            "GIT_ALTERNATE_OBJECT_DIRECTORIES",
        ] {
            command.env_remove(key);
        }
        let child = command
            .spawn()
            .context("Could not start git; check that Git is installed and on PATH")?;
        let mut running = RunningChild {
            child,
            active: true,
        };
        let start = Instant::now();
        let status = loop {
            if let Some(status) = running.child.try_wait()? {
                running.active = false;
                break status;
            }
            if self.cancel.load(Ordering::Relaxed) {
                bail!("Cancelled");
            }
            if start.elapsed() >= self.timeout {
                bail!(
                    "Git operation timed out after {} seconds",
                    self.timeout.as_secs()
                );
            }
            thread::sleep(Duration::from_millis(5));
        };
        Ok(Output {
            status,
            stdout: read(&mut stdout)?,
            stderr: String::from_utf8_lossy(&read(&mut stderr)?).into_owned(),
        })
    }

    pub fn checked(&self, path: &Path, args: &[&str]) -> Result<Vec<u8>> {
        let output = self.run(path, args)?;
        if !output.status.success() {
            if output.stderr.trim().is_empty() {
                bail!("Git operation failed: {}", output.status);
            }
            bail!("{}", output.stderr.trim());
        }
        Ok(output.stdout)
    }

    pub fn inspect(&self, path: &Path, fetch: bool) -> Report {
        let mut report = Report {
            path: path.into(),
            snapshot: None,
            verification: Verification::Cached,
            error: None,
        };
        let snapshot = match self.snapshot(path) {
            Ok(snapshot) => snapshot,
            Err(error) => {
                report.error = Some(error.to_string());
                return report;
            }
        };
        let eligible = snapshot.oid != "(initial)" && snapshot.branch != "(detached)";
        report.snapshot = Some(snapshot);
        if fetch
            && eligible
            && let Err(error) = self.fetch_upstream(&mut report)
        {
            report.verification = Verification::Failed(error.to_string());
        }
        report
    }

    fn snapshot(&self, path: &Path) -> Result<Snapshot> {
        Snapshot::parse(&self.checked(
            path,
            &[
                "status",
                "--porcelain=v2",
                "--branch",
                "--untracked-files=all",
                "-z",
            ],
        )?)
    }

    fn tracking(&self, path: &Path, branch: &str) -> Result<Tracking> {
        let output = self.checked(
            path,
            &[
                "for-each-ref",
                "--format=%(upstream)%00%(upstream:remotename)%00%(upstream:remoteref)",
                &format!("refs/heads/{branch}"),
            ],
        )?;
        let output = String::from_utf8(output).context("Upstream is not valid UTF-8")?;
        let fields: Vec<_> = output.trim_end_matches('\n').split('\0').collect();
        if fields.len() != 3 {
            bail!("Could not read upstream configuration");
        }
        Ok(Tracking {
            upstream: fields[0].into(),
            remote: fields[1].into(),
            remote_ref: fields[2].into(),
        })
    }

    fn fetch_upstream(&self, report: &mut Report) -> Result<()> {
        let branch = report
            .snapshot
            .as_ref()
            .context("Missing branch information")?
            .branch
            .clone();
        let tracking = self.tracking(&report.path, &branch)?;
        if tracking.upstream.is_empty() {
            report.verification = Verification::NoTarget;
            return Ok(());
        }
        if tracking.remote == "." {
            report.verification = Verification::Local;
            return Ok(());
        }
        if !tracking.upstream.starts_with("refs/remotes/")
            || !tracking.remote_ref.starts_with("refs/")
            || tracking.remote.is_empty()
        {
            bail!("Upstream is not a safe remote-tracking ref; fetch was skipped");
        }
        self.checked(
            &report.path,
            &[
                "fetch",
                "--quiet",
                "--no-tags",
                "--no-write-fetch-head",
                "--no-recurse-submodules",
                "--no-auto-maintenance",
                "--refmap=",
                "--",
                &tracking.remote,
                &format!("+{}:{}", tracking.remote_ref, tracking.upstream),
            ],
        )?;
        let checked_at = SystemTime::now();
        let updated = self.snapshot(&report.path)?;
        let same =
            updated.branch == branch && self.tracking(&report.path, &updated.branch)? == tracking;
        report.snapshot = Some(updated);
        if !same {
            bail!("The branch or upstream changed during the check. Please refresh.");
        }
        report.verification = Verification::Fetched(checked_at);
        Ok(())
    }
}

fn read(file: &mut File) -> Result<Vec<u8>> {
    file.seek(SeekFrom::Start(0))?;
    let mut bytes = Vec::new();
    file.read_to_end(&mut bytes)?;
    Ok(bytes)
}

#[derive(PartialEq, Eq)]
struct Tracking {
    upstream: String,
    remote: String,
    remote_ref: String,
}
