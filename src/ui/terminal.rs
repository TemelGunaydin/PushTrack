use super::{Action, App, draw};
use crate::{cli::Cli, config::FolderStore, scan::Scanner};
use anyhow::Result;
use crossterm::{
    cursor::Show,
    event::{self, Event, KeyEventKind},
    execute,
    terminal::{LeaveAlternateScreen, disable_raw_mode},
};
use std::{
    io,
    sync::{
        Arc,
        atomic::{AtomicBool, AtomicUsize, Ordering},
    },
    time::Duration,
};

struct RestoreTerminal;
impl Drop for RestoreTerminal {
    fn drop(&mut self) {
        let _ = disable_raw_mode();
        let _ = execute!(io::stdout(), Show, LeaveAlternateScreen);
    }
}

pub fn watch(
    cli: &Cli,
    store: FolderStore,
    cancel: Arc<AtomicBool>,
    signal: Arc<AtomicUsize>,
) -> Result<i32> {
    let mut scanner = Scanner::new(store, cli.paths.clone(), cli.fetch, cancel.clone())?;
    // Install the guard before initialization so partial initialization failures
    // also restore the shell. Ratatui additionally installs a panic hook.
    let _restore = RestoreTerminal;
    let mut terminal = ratatui::try_init()?;
    let mut app = App::new(cli.fetch, cli.colors(), cli.interval());
    scanner.start();
    loop {
        if cancel.load(Ordering::Relaxed) {
            return Ok(128 + signal.load(Ordering::Relaxed) as i32);
        }
        for update in scanner.updates.try_iter() {
            app.receive(update);
        }
        if !app.refreshing && std::time::Instant::now() >= app.next_check && scanner.start() {
            app.refreshing = true;
        }
        terminal.draw(|frame| draw(frame, &mut app))?;
        if event::poll(Duration::from_millis(80))?
            && let Event::Key(key) = event::read()?
        {
            if key.kind == KeyEventKind::Release {
                continue;
            }
            match app.key(key) {
                Action::Quit(code) => {
                    cancel.store(true, Ordering::Relaxed);
                    return Ok(code);
                }
                Action::Refresh if !app.refreshing && scanner.start() => {
                    app.refreshing = true;
                }
                _ => {}
            }
        }
    }
}
