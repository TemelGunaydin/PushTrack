use anyhow::Result;
use pushtrack::{
    discovery::discover,
    git::Git,
    model::{State, Verification},
};
use std::{
    fs,
    path::{Path, PathBuf},
    sync::atomic::Ordering,
    time::Duration,
};

struct Fixture {
    _temp: tempfile::TempDir,
    root: PathBuf,
    local: PathBuf,
    remote: PathBuf,
    git: Git,
}
impl Fixture {
    fn new() -> Result<Self> {
        let temp = tempfile::tempdir()?;
        let root = fs::canonicalize(temp.path())?;
        let local = root.join("local project");
        let remote = root.join("remote.git");
        let git = Git::default();
        git.checked(
            &root,
            &["init", "--initial-branch=main", local.to_str().unwrap()],
        )?;
        let fixture = Self {
            _temp: temp,
            root,
            local,
            remote,
            git,
        };
        fixture.configure(&fixture.local)?;
        Ok(fixture)
    }
    fn configure(&self, path: &Path) -> Result<()> {
        for (key, value) in [
            ("user.name", "PushTrack Tests"),
            ("user.email", "test@example.invalid"),
            ("commit.gpgsign", "false"),
            ("core.hooksPath", "/dev/null"),
        ] {
            self.git.checked(path, &["config", key, value])?;
        }
        Ok(())
    }
    fn commit(&self, path: &Path, file: &str, body: &str) -> Result<()> {
        fs::write(path.join(file), body)?;
        self.git.checked(path, &["add", "--", file])?;
        self.git.checked(path, &["commit", "-m", "Test commit"])?;
        Ok(())
    }
    fn setup_remote(&self) -> Result<()> {
        self.commit(&self.local, "initial.txt", "initial\n")?;
        self.git.checked(
            &self.root,
            &[
                "init",
                "--bare",
                "--initial-branch=main",
                self.remote.to_str().unwrap(),
            ],
        )?;
        self.git.checked(
            &self.local,
            &["remote", "add", "origin", self.remote.to_str().unwrap()],
        )?;
        self.git
            .checked(&self.local, &["push", "-u", "origin", "main"])?;
        Ok(())
    }
    fn peer(&self) -> Result<PathBuf> {
        let peer = self.root.join("peer");
        self.git.checked(
            &self.root,
            &[
                "clone",
                self.remote.to_str().unwrap(),
                peer.to_str().unwrap(),
            ],
        )?;
        self.configure(&peer)?;
        Ok(peer)
    }
}

#[test]
fn unborn_no_upstream_and_unpushed_commit_lifecycle() -> Result<()> {
    let f = Fixture::new()?;
    assert_eq!(f.git.inspect(&f.local, false).state(), State::Unborn);
    f.commit(&f.local, "first.txt", "first\n")?;
    assert_eq!(f.git.inspect(&f.local, true).state(), State::NoUpstream);
    f.setup_remote()?;
    assert_eq!(f.git.inspect(&f.local, false).state(), State::Synced);
    f.commit(&f.local, "pending.txt", "not pushed\n")?;
    let pending = f.git.inspect(&f.local, true);
    assert_eq!(pending.state(), State::Ahead);
    assert_eq!(pending.snapshot.unwrap().ahead, Some(1));
    assert!(matches!(pending.verification, Verification::Fetched(_)));
    f.git.checked(&f.local, &["push", "origin", "main"])?;
    assert_eq!(f.git.inspect(&f.local, true).state(), State::Synced);
    Ok(())
}

#[test]
fn synced_branch_still_detects_staged_modified_and_untracked_work() -> Result<()> {
    let f = Fixture::new()?;
    f.setup_remote()?;
    fs::write(f.local.join("initial.txt"), "not committed\n")?;
    fs::write(f.local.join("staged.txt"), "staged, not committed\n")?;
    f.git.checked(&f.local, &["add", "staged.txt"])?;
    fs::write(f.local.join("untracked.txt"), "not staged\n")?;
    let head = f.git.checked(&f.local, &["rev-parse", "HEAD"])?;
    let index = fs::read(f.local.join(".git/index"))?;
    for fetch in [false, true] {
        let report = f.git.inspect(&f.local, fetch);
        assert_eq!(
            report.state(),
            State::Synced,
            "History and working-tree state are independent"
        );
        assert!(
            !report.needs_push(),
            "Uncommitted files are not unpushed commits"
        );
        let snapshot = report.snapshot.unwrap();
        assert_eq!(
            (
                snapshot.staged,
                snapshot.modified,
                snapshot.untracked,
                snapshot.changed
            ),
            (1, 1, 1, 3)
        );
        assert_eq!(snapshot.worktree_status(), "● 3 uncommitted");
    }
    assert_eq!(f.git.checked(&f.local, &["rev-parse", "HEAD"])?, head);
    assert_eq!(fs::read(f.local.join(".git/index"))?, index);
    f.git.checked(&f.local, &["add", "--all"])?;
    f.git
        .checked(&f.local, &["commit", "-m", "Commit local work"])?;
    let committed = f.git.inspect(&f.local, false);
    assert_eq!(committed.state(), State::Ahead);
    assert!(committed.needs_push());
    assert_eq!(
        committed.snapshot.unwrap().worktree_status(),
        "✓ Working tree clean"
    );
    Ok(())
}

#[test]
fn stale_cache_behind_diverged_and_worktree_preservation() -> Result<()> {
    let f = Fixture::new()?;
    f.setup_remote()?;
    let peer = f.peer()?;
    f.commit(&peer, "peer.txt", "peer\n")?;
    f.git.checked(&peer, &["push", "origin", "main"])?;
    assert_eq!(f.git.inspect(&f.local, false).state(), State::Synced);
    assert_eq!(f.git.inspect(&f.local, true).state(), State::Behind);
    f.commit(&f.local, "local.txt", "local\n")?;
    fs::write(f.local.join("uncommitted.txt"), "preserve me")?;
    let head = f.git.checked(&f.local, &["rev-parse", "HEAD"])?;
    let remote = f.git.checked(&f.remote, &["rev-parse", "HEAD"])?;
    let index = fs::read(f.local.join(".git/index"))?;
    let report = f.git.inspect(&f.local, true);
    assert_eq!(report.state(), State::Diverged);
    let snapshot = report.snapshot.unwrap();
    assert_eq!(
        (snapshot.ahead, snapshot.behind, snapshot.untracked),
        (Some(1), Some(1), 1)
    );
    assert_eq!(f.git.checked(&f.local, &["rev-parse", "HEAD"])?, head);
    assert_eq!(f.git.checked(&f.remote, &["rev-parse", "HEAD"])?, remote);
    assert_eq!(fs::read(f.local.join(".git/index"))?, index);
    assert_eq!(fs::read(f.local.join("uncommitted.txt"))?, b"preserve me");
    Ok(())
}

#[test]
fn missing_ref_recovers_but_deleted_remote_branch_is_never_verified() -> Result<()> {
    let f = Fixture::new()?;
    f.setup_remote()?;
    f.git
        .checked(&f.local, &["update-ref", "-d", "refs/remotes/origin/main"])?;
    assert_eq!(f.git.inspect(&f.local, false).state(), State::MissingRef);
    assert_eq!(f.git.inspect(&f.local, true).state(), State::Synced);
    f.git
        .checked(&f.remote, &["update-ref", "-d", "refs/heads/main"])?;
    assert_eq!(f.git.inspect(&f.local, false).state(), State::Synced);
    let failed = f.git.inspect(&f.local, true);
    assert_eq!(failed.state(), State::Error);
    assert!(matches!(failed.verification, Verification::Failed(_)));
    Ok(())
}

#[test]
fn unavailable_remote_is_an_error_not_cached_green() -> Result<()> {
    let f = Fixture::new()?;
    f.setup_remote()?;
    f.git.checked(
        &f.local,
        &[
            "remote",
            "set-url",
            "origin",
            f.root.join("missing").to_str().unwrap(),
        ],
    )?;
    assert_eq!(f.git.inspect(&f.local, false).state(), State::Synced);
    assert_eq!(f.git.inspect(&f.local, true).state(), State::Error);
    Ok(())
}

#[test]
fn custom_refmaps_cannot_update_local_branches() -> Result<()> {
    let f = Fixture::new()?;
    f.setup_remote()?;
    f.git.checked(&f.local, &["branch", "protected"])?;
    let protected = f.git.checked(&f.local, &["rev-parse", "protected"])?;
    f.git.checked(
        &f.local,
        &[
            "config",
            "--add",
            "remote.origin.fetch",
            "+refs/heads/main:refs/heads/protected",
        ],
    )?;
    let peer = f.peer()?;
    f.commit(&peer, "peer.txt", "update\n")?;
    f.git.checked(&peer, &["push", "origin", "main"])?;
    assert_eq!(f.git.inspect(&f.local, true).state(), State::Behind);
    assert_eq!(
        f.git.checked(&f.local, &["rev-parse", "protected"])?,
        protected
    );
    Ok(())
}

#[test]
fn rename_paths_cannot_be_misread_as_status_records() -> Result<()> {
    let f = Fixture::new()?;
    let original = "? strange\nfilename";
    f.commit(&f.local, original, "rename me\n")?;
    f.commit(&f.local, "modified.txt", "before\n")?;
    f.git
        .checked(&f.local, &["mv", "--", original, "renamed.txt"])?;
    fs::write(f.local.join("modified.txt"), "after\n")?;
    fs::write(f.local.join("new\nfile.txt"), "new\n")?;
    let snapshot = f.git.inspect(&f.local, false).snapshot.unwrap();
    assert_eq!(
        (
            snapshot.staged,
            snapshot.modified,
            snapshot.untracked,
            snapshot.changed
        ),
        (1, 1, 1, 3)
    );
    assert_eq!(snapshot.branch, "main");
    Ok(())
}

#[test]
fn local_upstream_and_detached_head_remain_explicit() -> Result<()> {
    let f = Fixture::new()?;
    f.commit(&f.local, "file.txt", "content\n")?;
    f.git.checked(&f.local, &["branch", "other"])?;
    f.git
        .checked(&f.local, &["branch", "--set-upstream-to=other"])?;
    let local = f.git.inspect(&f.local, true);
    assert!(matches!(local.verification, Verification::Local));
    f.git.checked(&f.local, &["checkout", "--detach"])?;
    assert_eq!(f.git.inspect(&f.local, true).state(), State::Detached);
    Ok(())
}

#[test]
fn conflicts_are_counted_and_worktrees_discovered_once() -> Result<()> {
    let f = Fixture::new()?;
    f.commit(&f.local, "conflict.txt", "base\n")?;
    let worktree = f.root.join("worktree");
    f.git.checked(
        &f.local,
        &[
            "worktree",
            "add",
            "-b",
            "feature",
            worktree.to_str().unwrap(),
        ],
    )?;
    f.commit(&worktree, "conflict.txt", "feature\n")?;
    f.commit(&f.local, "conflict.txt", "main\n")?;
    assert!(!f.git.run(&f.local, &["merge", "feature"])?.status.success());
    assert_eq!(
        f.git.inspect(&f.local, false).snapshot.unwrap().conflicts,
        1
    );
    let found = discover(
        &[
            f.root.clone(),
            f.local.clone(),
            worktree.clone(),
            f.root.join("gone"),
        ],
        &f.git.cancel,
    );
    assert_eq!(found.repositories, [f.local.clone(), worktree.clone()]);
    assert_eq!(found.warnings.len(), 1);
    assert_eq!(
        f.git.inspect(&worktree, false).snapshot.unwrap().branch,
        "feature"
    );
    Ok(())
}

#[test]
fn repository_ssh_command_is_preserved_and_prompts_disabled() -> Result<()> {
    let f = Fixture::new()?;
    f.setup_remote()?;
    let helper = f.root.join("fake-ssh.sh");
    fs::write(
        &helper,
        "printf '%s' \"$SSH_ASKPASS_REQUIRE\" > ssh-used\nexit 1\n",
    )?;
    f.git.checked(
        &f.local,
        &[
            "config",
            "core.sshCommand",
            &format!("sh '{}'", helper.display()),
        ],
    )?;
    f.git.checked(
        &f.local,
        &["remote", "set-url", "origin", "ssh://127.0.0.1:1/repo"],
    )?;
    assert_eq!(f.git.inspect(&f.local, true).state(), State::Error);
    assert_eq!(fs::read(f.local.join("ssh-used"))?, b"force");
    Ok(())
}

#[test]
fn cancellation_and_large_output_are_safe() -> Result<()> {
    let git = Git::default();
    let temp = tempfile::tempdir()?;
    let bytes = git.checked(
        temp.path(),
        &["-c", "alias.output=!yes x | head -c 200000", "output"],
    )?;
    assert_eq!(bytes.len(), 200_000);
    git.cancel.store(true, Ordering::Relaxed);
    assert!(
        git.checked(Path::new("/path/does/not/exist"), &["--version"])
            .is_err()
    );
    Ok(())
}

#[test]
fn timeout_kills_transport_helpers() -> Result<()> {
    use nix::{sys::signal::kill, unistd::Pid};
    let temp = tempfile::tempdir()?;
    let git = Git {
        timeout: Duration::from_millis(300),
        ..Git::default()
    };
    assert!(
        git.run(
            temp.path(),
            &[
                "-c",
                "alias.waiter=!sleep 30 & echo $! > child.pid; wait",
                "waiter"
            ]
        )
        .is_err()
    );
    let pid: i32 = fs::read_to_string(temp.path().join("child.pid"))?
        .trim()
        .parse()?;
    let until = std::time::Instant::now() + Duration::from_secs(2);
    while kill(Pid::from_raw(pid), None).is_ok() && std::time::Instant::now() < until {
        std::thread::sleep(Duration::from_millis(10));
    }
    assert!(
        kill(Pid::from_raw(pid), None).is_err(),
        "Transport helper survived timeout"
    );
    Ok(())
}
