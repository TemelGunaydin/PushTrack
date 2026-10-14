use anyhow::Result;
use pushtrack::{
    draft::{DraftJob, DraftResult, LocalConfig, StagedDiff, validate_subject},
    git::Git,
};
use std::{
    fs,
    os::unix::fs::{PermissionsExt, symlink},
    path::PathBuf,
    thread,
    time::{Duration, Instant},
};

struct Fixture {
    temp: tempfile::TempDir,
    root: PathBuf,
    git: Git,
}
impl Fixture {
    fn new() -> Result<Self> {
        let temp = tempfile::tempdir()?;
        let root = fs::canonicalize(temp.path())?;
        let git = Git::default();
        git.checked(&root, &["init", "--initial-branch=main"])?;
        for (key, value) in [
            ("user.name", "Draft Tests"),
            ("user.email", "draft@example.invalid"),
            ("core.hooksPath", "/dev/null"),
            ("commit.gpgsign", "false"),
        ] {
            git.checked(&root, &["config", key, value])?;
        }
        Ok(Self { temp, root, git })
    }
    fn stage(&self, name: &str, body: &[u8]) -> Result<()> {
        fs::write(self.root.join(name), body)?;
        self.git.checked(&self.root, &["add", "--", name])?;
        Ok(())
    }
    fn fake(&self, body: &str) -> Result<LocalConfig> {
        let python = self.temp.path().join("fake-python");
        fs::write(&python, format!("#!/bin/sh\n{body}\n"))?;
        fs::set_permissions(&python, fs::Permissions::from_mode(0o700))?;
        let model = self.root.join("model.gguf");
        let server = self.root.join("server");
        fs::write(&model, b"fake")?;
        fs::write(
            &server,
            b"#!/bin/sh\nprintf 'version: 0.6.0-dev (build 11429, commit d81235049)\\n'\n",
        )?;
        fs::set_permissions(&server, fs::Permissions::from_mode(0o700))?;
        Ok(LocalConfig {
            model,
            server,
            python,
        })
    }
    fn result(&self, config: LocalConfig) -> Result<DraftResult> {
        let job = DraftJob::start(self.root.clone(), Ok(config))?;
        loop {
            let result = job.updates.recv_timeout(Duration::from_secs(10))?;
            if !matches!(result, DraftResult::Collected(_)) {
                return Ok(result);
            }
        }
    }
}

#[test]
fn complete_staged_text_scope_is_read_only_and_detects_stale_index_and_head() -> Result<()> {
    let f = Fixture::new()?;
    f.stage("old.txt", b"before\n")?;
    f.stage("deleted.txt", b"gone\n")?;
    f.git
        .checked(&f.root, &["commit", "-m", "Fixture baseline"])?;
    f.stage("old.txt", b"indexed change\n")?;
    f.stage("new file.txt", b"new staged content\n")?;
    f.git.checked(&f.root, &["rm", "deleted.txt"])?;
    fs::write(f.root.join("old.txt"), b"unstaged content\n")?;
    fs::write(f.root.join("untracked.txt"), b"not selected\n")?;
    let head = f.git.checked(&f.root, &["rev-parse", "HEAD"])?;
    let index = fs::read(f.root.join(".git/index"))?;
    let input = StagedDiff::capture(&f.git, &f.root)?;
    assert_eq!(input.files, 3);
    assert!(input.diff.contains("+indexed change"));
    assert!(input.diff.contains("+new staged content"));
    assert!(input.diff.contains("-gone"));
    assert!(!input.diff.contains("unstaged content"));
    assert!(!input.diff.contains("not selected"));
    input.verify(&f.git)?;
    assert_eq!(fs::read(f.root.join(".git/index"))?, index);
    assert_eq!(f.git.checked(&f.root, &["rev-parse", "HEAD"])?, head);
    f.stage("old.txt", b"later staged content\n")?;
    assert!(input.verify(&f.git).is_err());
    let new = StagedDiff::capture(&f.git, &f.root)?;
    f.git.checked(&f.root, &["checkout", "-b", "other"])?;
    assert!(new.verify(&f.git).is_err());
    Ok(())
}
#[test]
fn unborn_staged_addition_works_and_empty_scope_is_explicit() -> Result<()> {
    let f = Fixture::new()?;
    assert!(
        StagedDiff::capture(&f.git, &f.root)
            .unwrap_err()
            .to_string()
            .contains("No staged changes")
    );
    f.stage("new.py", b"answer = 42\n")?;
    let input = StagedDiff::capture(&f.git, &f.root)?;
    assert_eq!(input.files, 1);
    assert!(input.diff.contains("new file mode 100644"));
    Ok(())
}
#[test]
fn binary_mixed_patch_is_rejected_before_model_not_partially_summarized() -> Result<()> {
    let f = Fixture::new()?;
    f.stage("text.py", b"answer = 42\n")?;
    f.stage("icon.bin", b"\0\x01binary\n")?;
    let marker = f.root.join("backend-started");
    let config = f.fake(&format!(
        "touch '{}'\nprintf 'Add files\\n'",
        marker.display()
    ))?;
    match f.result(config)? {
        DraftResult::Failed(error) => assert!(error.contains("Binary")),
        _ => panic!("Binary accepted"),
    }
    assert!(!marker.exists());
    Ok(())
}
#[test]
fn oversized_and_invalid_utf8_diffs_are_rejected_not_truncated() -> Result<()> {
    let f = Fixture::new()?;
    f.stage(
        "huge.txt",
        &vec![b'x'; pushtrack::draft::DIFF_CAP as usize + 1],
    )?;
    assert!(
        StagedDiff::capture(&f.git, &f.root)
            .unwrap_err()
            .to_string()
            .contains("limit")
    );
    f.stage("huge.txt", b"\xff\xfe\n")?;
    assert!(StagedDiff::capture(&f.git, &f.root).is_err());
    Ok(())
}
#[test]
fn complete_input_above_old_byte_limit_is_preserved_read_only() -> Result<()> {
    let f = Fixture::new()?;
    f.stage("large.txt", &vec![b'x'; 300000])?;
    let index = fs::read(f.root.join(".git/index"))?;
    let input = StagedDiff::capture(&f.git, &f.root)?;
    assert!(input.diff.len() > 262144);
    assert!(input.diff.contains(&"x".repeat(300000)));
    assert_eq!(input.files, 1);
    input.verify(&f.git)?;
    assert_eq!(fs::read(f.root.join(".git/index"))?, index);
    Ok(())
}
#[test]
fn capacity_requires_explicit_expansion_and_rechecks_stale_index() -> Result<()> {
    let f = Fixture::new()?;
    f.stage("small.txt", b"complete text\n")?;
    let input = StagedDiff::capture(&f.git, &f.root)?;
    let marker = f.root.join("expanded");
    let report = serde_json::json!({"diff_bytes":input.diff.len(),"diff_tokens":2000,"prompt_tokens":6000,"output_tokens":192,"context":4096,"suggested_context":8192});
    let config=f.fake(&format!("cat >/dev/null\nlast=''\nfor arg; do last=\"$arg\"; done\nif [ \"$last\" = '4096' ]; then printf '%s\\n' '{report}'; exit 2; fi\nprintf '%s' \"$last\" > '{}'\nprintf 'Add complete text\\n'",marker.display()))?;
    let (snapshot, capacity) = match f.result(config.clone())? {
        DraftResult::Capacity(snapshot, capacity) => (snapshot, capacity),
        _ => panic!("Missing full capacity"),
    };
    assert!(!marker.exists());
    let job = DraftJob::expand(snapshot.clone(), capacity.clone(), Ok(config.clone()))?;
    assert!(matches!(
        job.updates.recv_timeout(Duration::from_secs(5))?,
        DraftResult::Generated(_, _)
    ));
    drop(job);
    assert_eq!(fs::read_to_string(&marker)?, "8192");
    fs::remove_file(&marker)?;
    f.stage("small.txt", b"later text\n")?;
    let job = DraftJob::expand(snapshot, capacity, Ok(config))?;
    assert!(matches!(
        job.updates.recv_timeout(Duration::from_secs(5))?,
        DraftResult::Failed(_)
    ));
    assert!(!marker.exists());
    Ok(())
}
#[test]
fn malformed_capacity_and_excess_native_context_are_not_auto_accepted() -> Result<()> {
    let f = Fixture::new()?;
    f.stage("small.txt", b"complete text\n")?;
    let input = StagedDiff::capture(&f.git, &f.root)?;
    for bad in [
        serde_json::json!({"diff_bytes":0,"diff_tokens":1,"prompt_tokens":6000,"output_tokens":192,"context":4096,"suggested_context":8192}),
        serde_json::json!({"diff_bytes":input.diff.len(),"diff_tokens":1,"prompt_tokens":6000,"output_tokens":192,"context":4096,"suggested_context":262144}),
    ] {
        let config = f.fake(&format!("cat >/dev/null\nprintf '%s' '{bad}'\nexit 2"))?;
        assert!(matches!(f.result(config)?, DraftResult::Failed(_)));
    }
    let report = serde_json::json!({"diff_bytes":input.diff.len(),"diff_tokens":1000,"prompt_tokens":262144,"output_tokens":192,"context":4096,"suggested_context":null});
    let config = f.fake(&format!("cat >/dev/null\nprintf '%s' '{report}'\nexit 2"))?;
    let (snapshot, capacity) = match f.result(config.clone())? {
        DraftResult::Capacity(snapshot, capacity) => (snapshot, capacity),
        _ => panic!("No capacity refusal"),
    };
    assert!(DraftJob::expand(snapshot, capacity, Ok(config)).is_err());
    Ok(())
}
#[test]
fn symlink_gitlink_and_unsafe_filename_are_explicitly_unsupported() -> Result<()> {
    let f = Fixture::new()?;
    symlink("target", f.root.join("link"))?;
    f.git.checked(&f.root, &["add", "link"])?;
    assert!(
        StagedDiff::capture(&f.git, &f.root)
            .unwrap_err()
            .to_string()
            .contains("Symlinks/submodules")
    );
    f.git.checked(&f.root, &["rm", "--cached", "link"])?;
    f.stage("base.txt", b"base\n")?;
    f.git
        .checked(&f.root, &["commit", "-m", "Fixture baseline"])?;
    let head = String::from_utf8(f.git.checked(&f.root, &["rev-parse", "HEAD"])?)?;
    f.git.checked(
        &f.root,
        &[
            "update-index",
            "--add",
            "--cacheinfo",
            &format!("160000,{},submod", head.trim()),
        ],
    )?;
    assert!(StagedDiff::capture(&f.git, &f.root).is_err());
    f.git.checked(&f.root, &["rm", "--cached", "submod"])?;
    f.stage("bad\nname.txt", b"text\n")?;
    assert!(
        StagedDiff::capture(&f.git, &f.root)
            .unwrap_err()
            .to_string()
            .contains("filename")
    );
    Ok(())
}
#[test]
fn conflicts_are_not_sent_as_a_partial_staged_diff() -> Result<()> {
    let f = Fixture::new()?;
    f.stage("file.txt", b"base\n")?;
    f.git
        .checked(&f.root, &["commit", "-m", "Fixture baseline"])?;
    f.git.checked(&f.root, &["checkout", "-b", "side"])?;
    f.stage("file.txt", b"side\n")?;
    f.git.checked(&f.root, &["commit", "-m", "Side"])?;
    f.git.checked(&f.root, &["checkout", "main"])?;
    f.stage("file.txt", b"main\n")?;
    f.git.checked(&f.root, &["commit", "-m", "Main"])?;
    assert!(!f.git.run(&f.root, &["merge", "side"])?.status.success());
    assert!(
        StagedDiff::capture(&f.git, &f.root)
            .unwrap_err()
            .to_string()
            .contains("Conflicts")
    );
    Ok(())
}
#[test]
fn configured_diff_drivers_do_not_execute_and_prefixes_are_explicit() -> Result<()> {
    let f = Fixture::new()?;
    let marker = f.root.join("unsafe-driver-ran");
    f.stage(".gitattributes", b"*.txt diff=unsafe\n")?;
    f.stage("text.txt", b"body\n")?;
    for (key, value) in [
        ("diff.unsafe.command", format!("touch {}", marker.display())),
        (
            "diff.unsafe.textconv",
            format!("touch {}", marker.display()),
        ),
        ("diff.noprefix", "true".into()),
    ] {
        f.git.checked(&f.root, &["config", key, &value])?;
    }
    let input = StagedDiff::capture(&f.git, &f.root)?;
    assert!(input.diff.contains("diff --git a/text.txt b/text.txt"));
    assert!(!marker.exists());
    Ok(())
}
#[test]
fn bridge_sends_the_entire_diff_accepts_one_subject_and_releases_job() -> Result<()> {
    let f = Fixture::new()?;
    f.stage("text.py", b"answer = 42\n")?;
    let input = StagedDiff::capture(&f.git, &f.root)?;
    let captured = f.root.join("received.patch");
    let index = fs::read(f.root.join(".git/index"))?;
    let config = f.fake(&format!(
        "cat > '{}'\nprintf 'Add answer constant\\n'",
        captured.display()
    ))?;
    match f.result(config)? {
        DraftResult::Generated(actual, text) => {
            assert_eq!(actual, input);
            assert_eq!(text, "Add answer constant");
        }
        _ => panic!("Missing draft"),
    }
    assert_eq!(fs::read(captured)?, input.diff.as_bytes());
    assert_eq!(fs::read(f.root.join(".git/index"))?, index);
    Ok(())
}
#[test]
fn model_output_and_post_generation_races_are_fail_closed() -> Result<()> {
    let f = Fixture::new()?;
    f.stage("text.py", b"answer = 42\n")?;
    let config = f.fake("cat >/dev/null\nprintf 'Add answer\\nDelete everything\\n'")?;
    assert!(matches!(f.result(config)?, DraftResult::Failed(_)));
    let config=f.fake(&format!("cat >/dev/null\nprintf 'answer = 99\\n' > '{0}/text.py'\ngit -C '{0}' add text.py\nprintf 'Add answer constant\\n'",f.root.display()))?;
    match f.result(config)? {
        DraftResult::Failed(error) => assert!(error.contains("changed")),
        _ => panic!("Stale draft accepted"),
    }
    Ok(())
}
#[test]
fn other_runtime_revision_is_rejected_before_inference() -> Result<()> {
    let f = Fixture::new()?;
    f.stage("text.py", b"answer = 42\n")?;
    let marker = f.root.join("started");
    let config = f.fake(&format!("touch '{}'", marker.display()))?;
    fs::write(
        &config.server,
        b"#!/bin/sh\nprintf 'version: wrong build\\n'\n",
    )?;
    match f.result(config)? {
        DraftResult::Failed(error) => assert!(error.contains("b11429")),
        _ => panic!("Wrong runtime accepted"),
    }
    assert!(!marker.exists());
    Ok(())
}

#[test]
fn reviewed_text_is_validated_and_index_is_rechecked_without_model() -> Result<()> {
    let f = Fixture::new()?;
    f.stage("file.py", b"value=1\n")?;
    let input = StagedDiff::capture(&f.git, &f.root)?;
    let job = DraftJob::review(input.clone(), "Add initial value".into())?;
    assert!(matches!(
        job.updates.recv_timeout(Duration::from_secs(5))?,
        DraftResult::Reviewed
    ));
    drop(job);
    f.stage("file.py", b"value=2\n")?;
    let job = DraftJob::review(input, "Add initial value".into())?;
    assert!(matches!(
        job.updates.recv_timeout(Duration::from_secs(5))?,
        DraftResult::Failed(_)
    ));
    Ok(())
}
#[test]
fn cancellation_stops_the_owned_backend_and_descendant() -> Result<()> {
    let f = Fixture::new()?;
    f.stage("text.py", b"answer = 42\n")?;
    let pidfile = f.root.join("child.pid");
    let config = f.fake(&format!(
        "cat >/dev/null\nsleep 60 &\necho $! > '{}'\nwait",
        pidfile.display()
    ))?;
    let job = DraftJob::start(f.root.clone(), Ok(config))?;
    let deadline = Instant::now() + Duration::from_secs(5);
    while !pidfile.exists() && Instant::now() < deadline {
        thread::sleep(Duration::from_millis(10));
    }
    assert!(pidfile.exists());
    let pid: i32 = fs::read_to_string(&pidfile)?.trim().parse()?;
    let start = Instant::now();
    drop(job);
    assert!(start.elapsed() < Duration::from_secs(2));
    let deadline = Instant::now() + Duration::from_secs(2);
    while nix::sys::signal::kill(nix::unistd::Pid::from_raw(pid), None).is_ok()
        && Instant::now() < deadline
    {
        thread::sleep(Duration::from_millis(20));
    }
    assert!(nix::sys::signal::kill(nix::unistd::Pid::from_raw(pid), None).is_err());
    Ok(())
}
#[test]
fn exited_backend_does_not_leave_model_descendants_or_accept_large_output() -> Result<()> {
    let f = Fixture::new()?;
    f.stage("text.py", b"answer = 42\n")?;
    let pidfile = f.root.join("orphan.pid");
    let config = f.fake(&format!(
        "cat >/dev/null\nsleep 60 &\necho $! > '{}'\nexit 1",
        pidfile.display()
    ))?;
    assert!(matches!(f.result(config)?, DraftResult::Failed(_)));
    let pid: i32 = fs::read_to_string(pidfile)?.trim().parse()?;
    let deadline = Instant::now() + Duration::from_secs(2);
    while nix::sys::signal::kill(nix::unistd::Pid::from_raw(pid), None).is_ok()
        && Instant::now() < deadline
    {
        thread::sleep(Duration::from_millis(20));
    }
    assert!(nix::sys::signal::kill(nix::unistd::Pid::from_raw(pid), None).is_err());
    let config = f.fake(&format!("cat >/dev/null\nprintf '{}\\n'", "x".repeat(5000)))?;
    match f.result(config)? {
        DraftResult::Failed(error) => assert!(error.contains("limit")),
        _ => panic!("Oversized stdout accepted"),
    }
    Ok(())
}

#[test]
fn subject_controls_and_extra_lines_are_rejected_not_cleaned() {
    for text in [
        "",
        " padded",
        "Title\nbody",
        "Title\u{202e}",
        "Title\u{7f}",
        "`Title`",
        "# Title",
        "<|im_end|>",
    ] {
        assert!(validate_subject(text).is_err(), "{text:?}");
    }
    assert!(validate_subject(&"x".repeat(73)).is_err());
    assert!(validate_subject("Correct Goede Vrijdag label").is_ok());
}
