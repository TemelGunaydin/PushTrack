use anyhow::{Result, bail};
use clap::Parser;
use crossterm::style::{Color, Stylize};
use pushtrack::{
    cli::{Cli, FolderCommand},
    config::FolderStore,
    discovery::discover,
    git::Git,
    model::{Report, State, safe},
    ui,
};
use signal_hook::consts::{SIGINT, SIGTERM};
use std::{
    io::{self, IsTerminal, Write},
    path::PathBuf,
    sync::{
        Arc,
        atomic::{AtomicBool, AtomicUsize, Ordering},
    },
};

fn main() {
    let cli = Cli::parse();
    let code = match run(cli) {
        Ok(code) => code,
        Err(error) => {
            eprintln!("pushtrack: {}", safe(format!("{error:#}")));
            1
        }
    };
    std::process::exit(code);
}

fn run(cli: Cli) -> Result<i32> {
    let store = FolderStore::from_environment()?;
    if cli.command.is_some() && (cli.fetch || cli.watch || !cli.paths.is_empty()) {
        bail!("Folder commands cannot be combined with scan paths, --fetch, or --watch");
    }
    if let Some(command) = &cli.command {
        let folders = match command {
            FolderCommand::Add { paths } => store.add(paths)?,
            FolderCommand::Remove { paths } => store.remove(paths)?,
            FolderCommand::List => store.load()?,
        };
        print_folders(&folders, &store)?;
        return Ok(0);
    }
    if cli.watch
        && (!io::stdin().is_terminal()
            || !io::stdout().is_terminal()
            || std::env::var("TERM").as_deref() == Ok("dumb"))
    {
        bail!(
            "--watch requires interactive terminal input and output. Omit --watch when piping output."
        );
    }
    let cancel = Arc::new(AtomicBool::new(false));
    let signal = Arc::new(AtomicUsize::new(0));
    for number in [SIGINT, SIGTERM] {
        signal_hook::flag::register_usize(number, signal.clone(), number as usize)?;
        signal_hook::flag::register(number, cancel.clone())?;
    }
    if cli.watch {
        return ui::watch(&cli, store, cancel, signal);
    }
    let roots = store.roots(&cli.paths, &std::env::current_dir()?)?;
    let found = discover(&roots, &cancel);
    let git = Git {
        cancel: cancel.clone(),
        ..Git::default()
    };
    let mut reports = vec![];
    for path in &found.repositories {
        if cancel.load(Ordering::Relaxed) {
            break;
        }
        reports.push(git.inspect(path, cli.fetch));
    }
    if cancel.load(Ordering::Relaxed) {
        return Ok(128 + signal.load(Ordering::Relaxed) as i32);
    }
    print_reports(&reports, &found.warnings, cli.colors(), cli.fetch)?;
    Ok(i32::from(
        reports.is_empty()
            || !found.warnings.is_empty()
            || reports.iter().any(|r| r.state() == State::Error),
    ))
}

fn print_folders(folders: &[PathBuf], store: &FolderStore) -> Result<()> {
    let mut output = io::stdout().lock();
    writeln!(output, "Saved folders ({}):", folders.len())?;
    for folder in folders {
        writeln!(output, "  {}", safe(folder.to_string_lossy()))?;
    }
    if folders.is_empty() {
        writeln!(
            output,
            "  No saved folders. Add one with: pushtrack add /path/to/projects"
        )?;
    }
    writeln!(
        output,
        "\nConfiguration: {}",
        safe(store.file.to_string_lossy())
    )?;
    Ok(())
}

fn print_reports(reports: &[Report], warnings: &[String], color: bool, fetch: bool) -> Result<()> {
    let mut output = io::stdout().lock();
    let pending = reports.iter().filter(|r| r.needs_push()).count();
    writeln!(
        output,
        "\n  >_ PushTrack\n  {} repositories · {pending} to push",
        reports.len()
    )?;
    writeln!(
        output,
        "  {}\n",
        if fetch {
            "Upstream checks · per-repository verification below"
        } else {
            "Cached local refs · remote not verified · use --fetch to check"
        }
    )?;
    if reports.is_empty() {
        writeln!(
            output,
            "  No Git repositories found. Use: pushtrack add /path/to/projects"
        )?;
    }
    for report in reports {
        let tone = match report.state() {
            State::Synced => Color::Green,
            State::Behind => Color::Blue,
            State::Error | State::Diverged => Color::Red,
            _ => Color::Yellow,
        };
        let status = if color {
            report.status().with(tone).to_string()
        } else {
            report.status()
        };
        let branch = report
            .snapshot
            .as_ref()
            .map(|s| safe(&s.branch))
            .unwrap_or_default();
        writeln!(
            output,
            "  {}  {branch}",
            safe(
                report
                    .path
                    .file_name()
                    .unwrap_or_default()
                    .to_string_lossy()
            )
        )?;
        writeln!(
            output,
            "    {status} · {}",
            report
                .snapshot
                .as_ref()
                .map(|s| s.changes())
                .unwrap_or_default()
        )?;
        let upstream = report
            .snapshot
            .as_ref()
            .and_then(|s| s.upstream.as_ref())
            .map(|u| format!(" → {}", safe(u)))
            .unwrap_or_default();
        writeln!(
            output,
            "    {}{upstream}",
            safe(report.path.to_string_lossy())
        )?;
        writeln!(output, "    {}", report.verification.label())?;
        if let Some(error) = report.issue() {
            writeln!(output, "    {}", safe(error))?;
        }
        writeln!(output)?;
    }
    for warning in warnings {
        writeln!(output, "  ! {}", safe(warning))?;
    }
    writeln!(
        output,
        "  S staged · M modified · ? untracked · U conflicts"
    )?;
    Ok(())
}
