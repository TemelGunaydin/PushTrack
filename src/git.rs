use crate::model::{Report, Snapshot, Verification};
pub use crate::process::Output;
use anyhow::{Context, Result, bail};
use std::{
    path::Path,
    process::Command,
    sync::{Arc, atomic::AtomicBool},
    time::{Duration, SystemTime},
};

#[derive(Clone)]
pub struct Git {
    pub cancel: Arc<AtomicBool>,
    pub timeout: Duration,
}

impl Default for Git {
    fn default() -> Self {
        Self {
            cancel: Arc::new(AtomicBool::new(false)),
            timeout: Duration::from_secs(20),
        }
    }
}

impl Git {
    pub fn run(&self, path: &Path, args: &[&str]) -> Result<Output> {
        self.run_bounded(path, args, None)
    }

    pub fn run_bounded(&self, path: &Path, args: &[&str], cap: Option<u64>) -> Result<Output> {
        let mut command = Command::new("git");
        command
            .args(["-c", "core.fsmonitor=false", "-c", "color.ui=false"])
            .args(args)
            .current_dir(path)
            .env("LC_ALL", "C")
            .env("GIT_OPTIONAL_LOCKS", "0")
            .env("GIT_NO_LAZY_FETCH", "1")
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
        crate::process::run(
            command,
            None,
            &self.cancel,
            self.timeout,
            cap,
            "Git operation",
        )
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

#[derive(PartialEq, Eq)]
struct Tracking {
    upstream: String,
    remote: String,
    remote_ref: String,
}
