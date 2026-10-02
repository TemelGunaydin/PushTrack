mod render;
mod terminal;
pub use render::draw;
pub use terminal::watch;

use crate::{model::Report, scan::Update};
use crossterm::event::{KeyCode, KeyEvent, KeyModifiers};
use ratatui::widgets::ListState;
use std::{
    collections::HashMap,
    path::PathBuf,
    time::{Duration, Instant, SystemTime},
};

#[derive(Clone)]
pub struct Entry {
    pub path: PathBuf,
    pub report: Option<Report>,
}

#[derive(Clone, Copy, PartialEq, Eq)]
pub enum Focus {
    Projects,
    Details,
}
#[derive(PartialEq, Eq, Debug)]
pub enum Action {
    None,
    Refresh,
    Quit(i32),
}

pub struct App {
    pub entries: Vec<Entry>,
    pub warnings: Vec<String>,
    pub list: ListState,
    pub focus: Focus,
    pub detail_scroll: u16,
    pub detail_max: u16,
    pub detail_page: u16,
    pub page_size: usize,
    pub refreshing: bool,
    pub completed: usize,
    pub last_check: Option<SystemTime>,
    pub next_check: Instant,
    pub interval: Duration,
    pub fetch: bool,
    pub color: bool,
}

impl App {
    pub fn new(fetch: bool, color: bool, interval: Duration) -> Self {
        Self {
            entries: vec![],
            warnings: vec![],
            list: ListState::default(),
            focus: Focus::Projects,
            detail_scroll: 0,
            detail_max: 0,
            detail_page: 1,
            page_size: 1,
            refreshing: true,
            completed: 0,
            last_check: None,
            next_check: Instant::now(),
            interval,
            fetch,
            color,
        }
    }

    pub fn receive(&mut self, update: Update) {
        match update {
            Update::Started { paths, warnings } => {
                let selected = self.selected().map(|e| e.path.clone());
                let mut old: HashMap<_, _> =
                    self.entries.drain(..).map(|e| (e.path, e.report)).collect();
                self.entries = paths
                    .into_iter()
                    .map(|path| Entry {
                        report: old.remove(&path).flatten(),
                        path,
                    })
                    .collect();
                let index = selected
                    .and_then(|path| self.entries.iter().position(|e| e.path == path))
                    .unwrap_or(self.list.selected().unwrap_or(0));
                self.select(index);
                self.warnings = warnings;
                self.completed = 0;
                self.refreshing = true;
            }
            Update::Report(report) => {
                if let Some(entry) = self.entries.iter_mut().find(|e| e.path == report.path) {
                    entry.report = Some(report);
                }
                self.completed += 1;
            }
            Update::Failed(error) => self.warnings = vec![error],
            Update::Finished(time) => {
                self.refreshing = false;
                self.last_check = Some(time);
                self.next_check = Instant::now() + self.interval;
            }
        }
    }

    pub fn selected(&self) -> Option<&Entry> {
        self.list.selected().and_then(|i| self.entries.get(i))
    }

    fn select(&mut self, index: usize) {
        let selected = if self.entries.is_empty() {
            None
        } else {
            Some(index.min(self.entries.len() - 1))
        };
        if self.list.selected() != selected {
            self.detail_scroll = 0;
        }
        self.list.select(selected);
    }

    pub fn key(&mut self, key: KeyEvent) -> Action {
        if key.code == KeyCode::Char('c') && key.modifiers.contains(KeyModifiers::CONTROL) {
            return Action::Quit(130);
        }
        match key.code {
            KeyCode::Char('q' | 'Q') => return Action::Quit(0),
            KeyCode::Char('r' | 'R') => return Action::Refresh,
            KeyCode::Tab | KeyCode::BackTab => {
                self.focus = if self.focus == Focus::Projects {
                    Focus::Details
                } else {
                    Focus::Projects
                };
            }
            code if self.focus == Focus::Details => {
                self.detail_scroll = match code {
                    KeyCode::Up | KeyCode::Char('k') => self.detail_scroll.saturating_sub(1),
                    KeyCode::Down | KeyCode::Char('j') => self.detail_scroll.saturating_add(1),
                    KeyCode::PageUp => self.detail_scroll.saturating_sub(self.detail_page),
                    KeyCode::PageDown => self.detail_scroll.saturating_add(self.detail_page),
                    KeyCode::Home => 0,
                    KeyCode::End => self.detail_max,
                    _ => self.detail_scroll,
                }
                .min(self.detail_max);
            }
            code => {
                let selected = self.list.selected().unwrap_or(0);
                let target = match code {
                    KeyCode::Up | KeyCode::Char('k') => selected.saturating_sub(1),
                    KeyCode::Down | KeyCode::Char('j') => selected.saturating_add(1),
                    KeyCode::PageUp => selected.saturating_sub(self.page_size),
                    KeyCode::PageDown => selected.saturating_add(self.page_size),
                    KeyCode::Home => 0,
                    KeyCode::End => self.entries.len().saturating_sub(1),
                    _ => selected,
                };
                self.select(target);
            }
        }
        Action::None
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    fn key(code: KeyCode) -> KeyEvent {
        KeyEvent::new(code, KeyModifiers::NONE)
    }
    #[test]
    fn selection_clamps_pages_and_survives_refresh_and_removal() {
        let mut app = App::new(false, false, Duration::from_secs(10));
        let paths: Vec<_> = (0..30)
            .map(|i| PathBuf::from(format!("/repo-{i:02}")))
            .collect();
        app.receive(Update::Started {
            paths: paths.clone(),
            warnings: vec![],
        });
        app.page_size = 5;
        app.key(key(KeyCode::Up));
        assert_eq!(app.list.selected(), Some(0));
        app.key(key(KeyCode::PageDown));
        assert_eq!(app.list.selected(), Some(5));
        app.receive(Update::Started {
            paths: paths[3..].to_vec(),
            warnings: vec![],
        });
        assert_eq!(app.selected().unwrap().path, paths[5]);
        app.key(key(KeyCode::End));
        app.key(key(KeyCode::Down));
        assert_eq!(app.selected().unwrap().path, paths[29]);
        app.receive(Update::Started {
            paths: vec![],
            warnings: vec![],
        });
        app.key(key(KeyCode::Down));
        assert!(app.selected().is_none());
        assert_eq!(app.key(key(KeyCode::Char('q'))), Action::Quit(0));
    }
    #[test]
    fn details_scroll_and_quit_work_while_fetching() {
        let mut app = App::new(true, false, Duration::from_secs(60));
        app.detail_max = 10;
        app.detail_page = 4;
        app.key(key(KeyCode::Tab));
        app.key(key(KeyCode::End));
        assert_eq!(app.detail_scroll, 10);
        app.key(key(KeyCode::Down));
        assert_eq!(app.detail_scroll, 10);
        app.key(key(KeyCode::PageUp));
        assert_eq!(app.detail_scroll, 6);
        assert_eq!(app.key(key(KeyCode::Char('r'))), Action::Refresh);
        assert_eq!(
            app.key(KeyEvent::new(KeyCode::Char('c'), KeyModifiers::CONTROL)),
            Action::Quit(130)
        );
    }
}
