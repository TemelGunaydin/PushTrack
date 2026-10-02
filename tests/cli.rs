use std::{
    fs,
    path::Path,
    process::{Command, Output},
};

fn cli(root: &Path, args: &[&str]) -> Output {
    Command::new(env!("CARGO_BIN_EXE_pushtrack"))
        .args(args)
        .env("XDG_CONFIG_HOME", root.join("config"))
        .env_remove("NO_COLOR")
        .current_dir(root)
        .output()
        .unwrap()
}
fn text(output: &Output) -> String {
    String::from_utf8_lossy(&output.stdout).into()
}

#[test]
fn saved_folder_commands_are_english_and_compatible() {
    let root = tempfile::tempdir().unwrap();
    let first = root.path().join("First Project");
    let second = root.path().join("Second Project");
    for path in [&first, &second] {
        assert!(
            Command::new("git")
                .args(["init", "--initial-branch=main"])
                .arg(path)
                .output()
                .unwrap()
                .status
                .success()
        );
    }
    let add = cli(
        root.path(),
        &["add", first.to_str().unwrap(), second.to_str().unwrap()],
    );
    assert!(
        add.status.success(),
        "{}",
        String::from_utf8_lossy(&add.stderr)
    );
    assert!(text(&add).contains("Saved folders (2)"));
    let saved = root.path().join("config/pushtrack/config.json");
    let before = fs::read(&saved).unwrap();
    let scan = cli(root.path(), &[]);
    assert!(scan.status.success());
    assert!(text(&scan).contains("2 repositories"));
    assert!(text(&scan).contains("No commits yet"));
    assert!(!text(&scan).contains('\x1b'));
    assert!(
        text(&cli(
            root.path(),
            &[first.to_str().unwrap(), "--color", "always"]
        ))
        .contains('\x1b')
    );
    assert_eq!(
        fs::read(&saved).unwrap(),
        before,
        "One-off scan changed saved folders"
    );
    assert!(
        !cli(root.path(), &["add", "/this/folder/does/not/exist"])
            .status
            .success()
    );
    assert_eq!(fs::read(&saved).unwrap(), before);
    assert!(
        cli(root.path(), &["remove", second.to_str().unwrap()])
            .status
            .success()
    );
    assert!(text(&cli(root.path(), &["list"])).contains("Saved folders (1)"));
    assert!(text(&cli(root.path(), &["--help"])).contains("keyboard-driven dashboard"));
}

#[test]
fn watch_requires_interactive_input_and_output() {
    let root = tempfile::tempdir().unwrap();
    let result = cli(root.path(), &["--watch"]);
    assert_eq!(result.status.code(), Some(1));
    assert!(String::from_utf8_lossy(&result.stderr).contains("requires interactive terminal"));
    assert!(!text(&result).contains("\x1b[?1049h"));
}
