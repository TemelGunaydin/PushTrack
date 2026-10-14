use super::{Action, App, DraftDialog, DraftPhase, ModelManager, ModelPhase, draw};
use crate::{
    assets::{AssetJob, Update as AssetUpdate},
    cli::Cli,
    config::FolderStore,
    draft::{DraftJob, DraftResult},
    scan::Scanner,
};
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
    let mut draft_job: Option<DraftJob> = None;
    let mut asset_job: Option<AssetJob> = None;
    let mut local = cli.local.clone();
    loop {
        if cancel.load(Ordering::Relaxed) {
            return Ok(128 + signal.load(Ordering::Relaxed) as i32);
        }
        for update in scanner.updates.try_iter() {
            app.receive(update);
        }
        if let Some(job) = &draft_job {
            let result = match job.updates.try_recv() {
                Ok(result) => Some(result),
                Err(std::sync::mpsc::TryRecvError::Disconnected) => Some(DraftResult::Failed(
                    "Local draft worker exited unexpectedly".into(),
                )),
                Err(std::sync::mpsc::TryRecvError::Empty) => None,
            };
            if let Some(result) = result {
                let finished = !matches!(result, DraftResult::Collected(_));
                if let Some(dialog) = &mut app.draft {
                    match result {
                        DraftResult::Collected(input) => dialog.input = Some(input),
                        DraftResult::Capacity(input, capacity) => {
                            dialog.input = Some(input);
                            dialog.capacity = Some(capacity);
                            dialog.phase = DraftPhase::Capacity;
                        }
                        DraftResult::Generated(input, text) => {
                            dialog.input = Some(input);
                            dialog.text = text;
                            dialog.phase = DraftPhase::Editing;
                        }
                        DraftResult::Reviewed => dialog.phase = DraftPhase::Reviewed,
                        DraftResult::Failed(error) => {
                            dialog.error = error;
                            dialog.phase = DraftPhase::Error;
                            dialog.text.clear();
                        }
                    }
                }
                if finished {
                    draft_job = None;
                }
            }
        }
        if let Some(job) = &asset_job {
            let mut finished = false;
            loop {
                let update = match job.updates.try_recv() {
                    Ok(update) => update,
                    Err(std::sync::mpsc::TryRecvError::Empty) => break,
                    Err(std::sync::mpsc::TryRecvError::Disconnected) => {
                        if !finished && let Some(models) = &mut app.models {
                            models.phase = ModelPhase::Error;
                            models.error =
                                "Model install worker exited unexpectedly; partials preserved"
                                    .into();
                        }
                        finished = true;
                        break;
                    }
                };
                if let Some(models) = &mut app.models {
                    match update {
                        AssetUpdate::Progress(progress) => models.progress = Some(progress),
                        AssetUpdate::Ready(path) => {
                            local.ai_model = Some(path.clone());
                            models.selected_path = Some(path);
                            models.phase = ModelPhase::Ready;
                            finished = true;
                        }
                        AssetUpdate::Failed(error) => {
                            models.phase = ModelPhase::Error;
                            models.error = error;
                            finished = true;
                        }
                    }
                }
            }
            if finished {
                asset_job = None;
            }
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
                Action::OpenModels => app.models = Some(ModelManager::new(local.ai_model.clone())),
                Action::CloseModels => {
                    asset_job = None;
                    app.models = None;
                }
                Action::DownloadModel | Action::SelectModel => {
                    let result = if matches!(
                        app.models.as_ref().map(|model| model.phase),
                        Some(ModelPhase::Confirm)
                    ) {
                        AssetJob::download()
                    } else {
                        app.models
                            .as_ref()
                            .and_then(|model| model.path())
                            .ok_or_else(|| anyhow::anyhow!("No model path selected"))
                            .and_then(AssetJob::verify)
                    };
                    if let Some(models) = &mut app.models {
                        match result {
                            Ok(job) => {
                                asset_job = Some(job);
                                models.phase = ModelPhase::Busy;
                                models.progress = None;
                                models.error.clear();
                            }
                            Err(error) => {
                                models.phase = ModelPhase::Error;
                                models.error = error.to_string();
                            }
                        }
                    }
                }
                Action::GenerateDraft => {
                    if local.ai_model.is_none()
                        && !crate::assets::model_path().is_ok_and(|path| path.is_file())
                    {
                        app.models = Some(ModelManager::new(None));
                        continue;
                    }
                    if let Some(entry) = app.selected() {
                        let path = entry.path.clone();
                        app.draft = Some(DraftDialog::new(path.clone()));
                        match DraftJob::start(path, local.config()) {
                            Ok(job) => draft_job = Some(job),
                            Err(error) => {
                                let dialog = app.draft.as_mut().unwrap();
                                dialog.phase = DraftPhase::Error;
                                dialog.error = error.to_string();
                            }
                        }
                    }
                }
                Action::ExpandDraft => {
                    if let Some(dialog) = app.draft.as_mut()
                        && let Some(input) = dialog.input.clone()
                        && let Some(capacity) = dialog.capacity.clone()
                    {
                        dialog.phase = DraftPhase::Generating;
                        match DraftJob::expand(input, capacity, local.config()) {
                            Ok(job) => draft_job = Some(job),
                            Err(error) => {
                                dialog.error = error.to_string();
                                dialog.phase = DraftPhase::Error;
                            }
                        }
                    }
                }
                Action::CloseDraft => {
                    draft_job = None;
                    app.draft = None;
                }
                Action::ReviewDraft => {
                    if let Some(dialog) = app.draft.as_mut()
                        && let Some(input) = dialog.input.clone()
                    {
                        match DraftJob::review(input, dialog.text.clone()) {
                            Ok(job) => {
                                dialog.phase = DraftPhase::Checking;
                                draft_job = Some(job);
                            }
                            Err(error) => {
                                dialog.phase = DraftPhase::Error;
                                dialog.error = error.to_string();
                            }
                        }
                    }
                }
                Action::Refresh if !app.refreshing && scanner.start() => {
                    app.refreshing = true;
                }
                _ => {}
            }
        }
    }
}
