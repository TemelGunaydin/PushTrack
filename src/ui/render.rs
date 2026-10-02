use super::{App, Focus};
use crate::model::{State, clock, safe};
use ratatui::{
    Frame,
    layout::{Constraint, Layout, Rect},
    style::{Color, Modifier, Style},
    text::{Line, Span, Text},
    widgets::{
        Block, BorderType, Borders, List, ListItem, Padding, Paragraph, Scrollbar,
        ScrollbarOrientation, ScrollbarState, Wrap,
    },
};

#[derive(Clone, Copy)]
struct Theme {
    bg: Color,
    panel: Color,
    text: Color,
    muted: Color,
    border: Color,
    mint: Color,
    amber: Color,
    red: Color,
    blue: Color,
    selected: Color,
}
impl Theme {
    fn new(color: bool) -> Self {
        let rgb = |r, g, b| {
            if color {
                Color::Rgb(r, g, b)
            } else {
                Color::Reset
            }
        };
        Self {
            bg: rgb(13, 18, 25),
            panel: rgb(18, 25, 35),
            text: rgb(220, 228, 237),
            muted: rgb(129, 146, 164),
            border: rgb(44, 58, 73),
            mint: rgb(82, 219, 175),
            amber: rgb(245, 190, 98),
            red: rgb(244, 112, 126),
            blue: rgb(115, 177, 245),
            selected: rgb(27, 49, 60),
        }
    }
    fn status(self, state: State) -> Color {
        match state {
            State::Synced => self.mint,
            State::Behind => self.blue,
            State::Error | State::Diverged => self.red,
            _ => self.amber,
        }
    }
    fn block(self, title: &'static str, focused: bool) -> Block<'static> {
        Block::default()
            .borders(Borders::ALL)
            .border_type(BorderType::Rounded)
            .border_style(Style::default().fg(if focused { self.mint } else { self.border }))
            .style(Style::default().fg(self.text).bg(self.panel))
            .title(
                Line::from(title).style(
                    Style::default()
                        .fg(if focused { self.mint } else { self.muted })
                        .bold(),
                ),
            )
    }
}

pub fn draw(frame: &mut Frame, app: &mut App) {
    let theme = Theme::new(app.color);
    let area = frame.area();
    frame.render_widget(
        Block::new().style(Style::default().fg(theme.text).bg(theme.bg)),
        area,
    );
    if area.width < 60 || area.height < 18 {
        let text = Text::from(vec![
            Line::styled(" >_ PushTrack", Style::default().fg(theme.mint).bold()),
            Line::from(" Resize the terminal to at least 60 × 18."),
            Line::from(" q quit · Ctrl+C exit"),
        ]);
        frame.render_widget(Paragraph::new(text), area);
        return;
    }
    let [header, metrics, spacer, body, footer] = Layout::vertical([
        Constraint::Length(3),
        Constraint::Length(3),
        Constraint::Length(1),
        Constraint::Min(5),
        Constraint::Length(3),
    ])
    .margin(1)
    .areas(area);
    header_view(frame, app, header, theme);
    metrics_view(frame, app, metrics, theme);
    frame.render_widget(Paragraph::new(""), spacer);
    let [projects, details] = if area.width >= 110 {
        Layout::horizontal([Constraint::Percentage(54), Constraint::Percentage(46)])
            .spacing(1)
            .areas(body)
    } else {
        Layout::vertical([Constraint::Percentage(55), Constraint::Percentage(45)]).areas(body)
    };
    projects_view(frame, app, projects, theme);
    details_view(frame, app, details, theme);
    footer_view(frame, app, footer, theme);
}

fn header_view(frame: &mut Frame, app: &App, area: Rect, theme: Theme) {
    let [brand, mode] =
        Layout::horizontal([Constraint::Min(20), Constraint::Length(24)]).areas(area);
    frame.render_widget(
        Paragraph::new(vec![
            Line::from(vec![
                Span::styled(" >_ ", Style::default().fg(theme.mint).bold()),
                Span::styled("PUSHTRACK", Style::default().fg(theme.text).bold()),
            ]),
            Line::styled(
                " Your work. Nothing left behind.",
                Style::default().fg(theme.muted),
            ),
        ]),
        brand,
    );
    let label = if app.fetch {
        "◉  FETCH + WATCH"
    } else {
        "◉  LOCAL WATCH"
    };
    frame.render_widget(
        Paragraph::new(vec![
            Line::styled(label, Style::default().fg(theme.mint).bold()),
            Line::styled("Never commits or pushes", Style::default().fg(theme.muted)),
        ])
        .right_aligned(),
        mode,
    );
}

fn metrics_view(frame: &mut Frame, app: &App, area: Rect, theme: Theme) {
    let reports: Vec<_> = app
        .entries
        .iter()
        .filter_map(|e| e.report.as_ref())
        .collect();
    let pending = reports.iter().filter(|r| r.needs_push()).count();
    let dirty = reports
        .iter()
        .filter(|r| r.snapshot.as_ref().is_some_and(|s| s.changed > 0))
        .count();
    let attention = reports
        .iter()
        .filter(|r| {
            matches!(
                r.state(),
                State::Error
                    | State::Diverged
                    | State::MissingRef
                    | State::NoUpstream
                    | State::Detached
            ) || r.snapshot.as_ref().is_some_and(|s| s.conflicts > 0)
        })
        .count()
        + app.warnings.len();
    let compact = area.width < 100;
    let areas = Layout::horizontal([Constraint::Ratio(1, 4); 4])
        .spacing(1)
        .split(area);
    for (area, (title, number, color)) in areas.iter().zip([
        (
            if compact { " REPOS " } else { " REPOSITORIES " },
            app.entries.len(),
            theme.text,
        ),
        (" TO PUSH ", pending, theme.amber),
        (
            if compact {
                " CHANGES "
            } else {
                " WORK IN PROGRESS "
            },
            dirty,
            theme.blue,
        ),
        (
            if compact {
                " ATTENTION "
            } else {
                " NEED ATTENTION "
            },
            attention,
            theme.red,
        ),
    ]) {
        let block = theme.block(title, false);
        frame.render_widget(
            Paragraph::new(format!(" {number:02}"))
                .style(Style::default().fg(color).bold())
                .block(block),
            *area,
        );
    }
}

fn projects_view(frame: &mut Frame, app: &mut App, area: Rect, theme: Theme) {
    let selected = app.list.selected().map_or(0, |i| i + 1);
    let block = theme
        .block(" PROJECTS ", app.focus == Focus::Projects)
        .title(Line::from(format!(" {selected} / {} ", app.entries.len())).right_aligned());
    let inner = block.inner(area);
    app.page_size = (inner.height as usize / 2).max(1);
    if app.entries.is_empty() {
        let message = if app.refreshing {
            "\n  Discovering repositories…"
        } else {
            "\n  No repositories found.\n\n  pushtrack add /path/to/projects"
        };
        frame.render_widget(
            Paragraph::new(message)
                .style(Style::default().fg(theme.muted))
                .block(block),
            area,
        );
        return;
    }
    let items: Vec<_> = app
        .entries
        .iter()
        .map(|entry| {
            let name = safe(entry.path.file_name().unwrap_or_default().to_string_lossy());
            let branch = entry
                .report
                .as_ref()
                .and_then(|r| r.snapshot.as_ref())
                .map(|s| safe(&s.branch))
                .unwrap_or_default();
            let (status, color, changes) = match &entry.report {
                Some(report) => (
                    report.status(),
                    theme.status(report.state()),
                    report
                        .snapshot
                        .as_ref()
                        .map(|s| s.changes())
                        .unwrap_or_default(),
                ),
                None => ("· Waiting for check".into(), theme.muted, String::new()),
            };
            ListItem::new(vec![
                Line::from(vec![
                    Span::styled(format!(" {name}"), Style::default().fg(theme.text).bold()),
                    Span::styled(format!("  {branch}"), Style::default().fg(theme.muted)),
                ]),
                Line::from(vec![
                    Span::styled(format!(" {status}"), Style::default().fg(color)),
                    Span::styled(format!("  {changes}"), Style::default().fg(theme.muted)),
                ]),
            ])
        })
        .collect();
    let highlight = if app.color {
        Style::default().bg(theme.selected)
    } else {
        Style::default().add_modifier(Modifier::REVERSED)
    };
    let list = List::new(items)
        .block(block)
        .highlight_symbol("▎")
        .highlight_style(highlight);
    frame.render_stateful_widget(list, area, &mut app.list);
    if app.entries.len() > app.page_size && area.height > 2 {
        let mut scrollbar = ScrollbarState::new(app.entries.len() * 2)
            .position(app.list.offset() * 2)
            .viewport_content_length(inner.height as usize);
        frame.render_stateful_widget(
            Scrollbar::new(ScrollbarOrientation::VerticalRight)
                .begin_symbol(None)
                .end_symbol(None)
                .thumb_style(Style::default().fg(theme.mint))
                .track_style(Style::default().fg(theme.border)),
            area.inner(ratatui::layout::Margin {
                horizontal: 0,
                vertical: 1,
            }),
            &mut scrollbar,
        );
    }
}

fn details_view(frame: &mut Frame, app: &mut App, area: Rect, theme: Theme) {
    let block = theme
        .block(" DETAILS ", app.focus == Focus::Details)
        .padding(Padding::horizontal(1));
    let inner = block.inner(area);
    let mut lines = vec![];
    if let Some(entry) = app.selected() {
        lines.push(Line::styled(
            safe(entry.path.file_name().unwrap_or_default().to_string_lossy()),
            Style::default().fg(theme.text).bold(),
        ));
        if let Some(report) = &entry.report {
            lines.push(Line::styled(
                report.status(),
                Style::default().fg(theme.status(report.state())).bold(),
            ));
            lines.push(Line::styled(
                report.verification.label(),
                Style::default().fg(theme.muted),
            ));
            if let Some(error) = report.issue() {
                lines.push(Line::from(""));
                lines.push(Line::styled(safe(error), Style::default().fg(theme.red)));
            }
            if let Some(snapshot) = &report.snapshot {
                lines.push(Line::from(""));
                lines.push(Line::styled(
                    "BRANCH → UPSTREAM",
                    Style::default().fg(theme.muted),
                ));
                lines.push(Line::from(safe(format!(
                    "{} → {}",
                    snapshot.branch,
                    snapshot.upstream.as_deref().unwrap_or("not configured")
                ))));
                lines.push(Line::from(""));
                lines.push(Line::styled(
                    "WORKING TREE",
                    Style::default().fg(theme.muted),
                ));
                lines.push(Line::from(format!(
                    "{} staged    {} modified",
                    snapshot.staged, snapshot.modified
                )));
                lines.push(Line::styled(
                    format!(
                        "{} untracked    {} conflicts",
                        snapshot.untracked, snapshot.conflicts
                    ),
                    Style::default().fg(if snapshot.conflicts > 0 {
                        theme.red
                    } else {
                        theme.text
                    }),
                ));
            }
        } else {
            lines.push(Line::styled(
                "Waiting for check…",
                Style::default().fg(theme.muted),
            ));
            lines.push(Line::from("You can navigate while Git is working."));
        }
        lines.push(Line::from(""));
        lines.push(Line::styled("LOCATION", Style::default().fg(theme.muted)));
        lines.push(Line::from(safe(entry.path.to_string_lossy())));
    } else {
        lines.push(Line::from("Select a repository to inspect its status."));
    }
    if !app.warnings.is_empty() {
        lines.push(Line::from(""));
        lines.push(Line::styled(
            "SCAN WARNINGS",
            Style::default().fg(theme.amber).bold(),
        ));
        for warning in &app.warnings {
            lines.push(Line::styled(
                safe(warning),
                Style::default().fg(theme.amber),
            ));
        }
    }
    lines.push(Line::from(""));
    lines.push(Line::styled(if app.fetch { "Fetch verifies the configured upstream at a point in time, not alternate push destinations." } else { "Local refs can be stale. Use --fetch to verify the remote." }, Style::default().fg(theme.muted)));
    let paragraph = Paragraph::new(lines).wrap(Wrap { trim: false });
    app.detail_max = paragraph
        .line_count(inner.width)
        .saturating_sub(inner.height as usize)
        .min(u16::MAX as usize) as u16;
    app.detail_scroll = app.detail_scroll.min(app.detail_max);
    app.detail_page = inner.height.max(1);
    let block = if app.detail_max > 0 {
        block.title(Line::from(" Tab · ↑↓ scroll ").right_aligned())
    } else {
        block
    };
    frame.render_widget(paragraph.scroll((app.detail_scroll, 0)).block(block), area);
}

fn footer_view(frame: &mut Frame, app: &App, area: Rect, theme: Theme) {
    let progress = if app.refreshing {
        format!(
            "Checking {} / {} · navigation stays active",
            app.completed,
            app.entries.len()
        )
    } else {
        let seconds = app
            .next_check
            .saturating_duration_since(std::time::Instant::now())
            .as_secs();
        format!(
            "Last scan {} · refresh in {seconds}s",
            app.last_check.map(clock).unwrap_or_else(|| "—".into())
        )
    };
    let mode = if app.fetch {
        "UPSTREAM"
    } else {
        "LOCAL · remote not verified"
    };
    let warning = if app.warnings.is_empty() {
        String::new()
    } else {
        format!(" · {} warning(s), see Details", app.warnings.len())
    };
    frame.render_widget(
        Paragraph::new(vec![
            Line::styled(
                format!(" {mode} · {progress}{warning}"),
                Style::default().fg(theme.muted),
            ),
            Line::from(vec![
                Span::styled(" ↑↓ ", Style::default().fg(theme.mint).bold()),
                Span::raw("move  "),
                Span::styled("PgUp/Dn ", Style::default().fg(theme.mint)),
                Span::raw("page  "),
                Span::styled("Tab ", Style::default().fg(theme.mint)),
                Span::raw("details  "),
                Span::styled("r ", Style::default().fg(theme.mint)),
                Span::raw("refresh  "),
                Span::styled("q ", Style::default().fg(theme.mint)),
                Span::raw("quit"),
            ]),
            Line::styled(
                " S staged · M modified · ? untracked · U conflicts",
                Style::default().fg(theme.muted),
            ),
        ]),
        area,
    );
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{
        model::{Report, Snapshot, Verification},
        scan::Update,
    };
    use crossterm::event::{KeyCode, KeyEvent, KeyModifiers};
    use ratatui::{Terminal, backend::TestBackend};
    use std::time::Duration;

    #[test]
    fn dashboard_is_bounded_and_scrolls_to_last_repository() {
        for (width, height) in [(140, 36), (80, 24), (60, 18), (30, 8), (1, 1)] {
            let mut app = App::new(false, true, Duration::from_secs(10));
            let paths: Vec<_> = (0..50)
                .map(|n| format!("/projects/repo-{n:02}").into())
                .collect();
            app.receive(Update::Started {
                paths,
                warnings: vec![],
            });
            app.key(KeyEvent::new(KeyCode::End, KeyModifiers::NONE));
            let mut terminal = Terminal::new(TestBackend::new(width, height)).unwrap();
            terminal.draw(|frame| draw(frame, &mut app)).unwrap();
            let buffer = terminal.backend().buffer();
            assert_eq!(buffer.area.width, width);
            assert_eq!(buffer.area.height, height);
            let text: String = buffer.content.iter().map(|c| c.symbol()).collect();
            if width >= 60 && height >= 18 {
                assert!(text.contains("repo-49"));
                assert!(text.contains("q quit"));
                assert!(text.contains("PROJECTS"));
            }
        }
    }

    #[test]
    fn failure_never_renders_as_in_sync_and_controls_are_sanitized() {
        let mut app = App::new(true, false, Duration::from_secs(60));
        let path = "/repo\x1b[2J".into();
        app.receive(Update::Started {
            paths: vec![path],
            warnings: vec![],
        });
        app.receive(Update::Report(Report {
            path: app.entries[0].path.clone(),
            snapshot: Some(Snapshot {
                branch: "main".into(),
                oid: "abc".into(),
                upstream: Some("origin/main".into()),
                ahead: Some(0),
                behind: Some(0),
                ..Snapshot::default()
            }),
            verification: Verification::Failed("No connection".into()),
            error: None,
        }));
        let mut terminal = Terminal::new(TestBackend::new(140, 36)).unwrap();
        terminal.draw(|frame| draw(frame, &mut app)).unwrap();
        let text: String = terminal
            .backend()
            .buffer()
            .content
            .iter()
            .map(|c| c.symbol())
            .collect();
        assert!(text.contains("Check failed"));
        assert!(text.contains("Remote not verified"));
        assert!(!text.contains("In sync"));
        assert!(!text.contains('\x1b'));
    }
}
