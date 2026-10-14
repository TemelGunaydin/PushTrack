use super::{App, DraftPhase, Focus, ModelPhase};
use crate::model::{Snapshot, State, clock, safe};
use ratatui::{
    Frame,
    layout::{Constraint, Layout, Rect},
    style::{Color, Modifier, Style},
    text::{Line, Span, Text},
    widgets::{
        Block, BorderType, Borders, Clear, Gauge, List, ListItem, Padding, Paragraph, Scrollbar,
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
    fn worktree(self, snapshot: &Snapshot) -> Color {
        if snapshot.conflicts > 0 {
            self.red
        } else if snapshot.changed > 0 {
            self.amber
        } else {
            self.mint
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
            Line::from(if app.draft.is_some() || app.models.is_some() {
                " Esc close/cancel · Ctrl+C exit"
            } else {
                " q quit · Ctrl+C exit"
            }),
        ]);
        frame.render_widget(Paragraph::new(text), area);
        return;
    }
    // Keep room for a complete two-line project row in short terminals.
    let short = area.height < 24;
    let [header, metrics, spacer, body, footer] = Layout::vertical([
        Constraint::Length(if short { 2 } else { 3 }),
        Constraint::Length(3),
        Constraint::Length(if short { 0 } else { 1 }),
        Constraint::Min(5),
        Constraint::Length(if short { 2 } else { 3 }),
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
    if app.draft.is_some() || app.models.is_some() {
        // Desaturate the dashboard, including selection/status colors. Clear below
        // resets the foreground cells so modal text never inherits DIM.
        let backdrop = Style::default()
            .fg(theme.muted)
            .bg(theme.bg)
            .remove_modifier(Modifier::BOLD | Modifier::REVERSED)
            .add_modifier(Modifier::DIM);
        for cell in &mut frame.buffer_mut().content {
            cell.set_style(backdrop);
        }
    }
    if app.draft.is_some() {
        draft_view(frame, app, theme);
    }
    if app.models.is_some() {
        models_view(frame, app, theme);
    }
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
            ) || r.snapshot.as_ref().is_some_and(|s| s.changed > 0)
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
                " UNCOMMITTED "
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
            let mut status_line = vec![];
            if let Some(snapshot) = entry.report.as_ref().and_then(|r| r.snapshot.as_ref())
                && snapshot.changed > 0
            {
                status_line.push(Span::styled(
                    format!(" {}", snapshot.worktree_status()),
                    Style::default().fg(theme.worktree(snapshot)).bold(),
                ));
                status_line.push(Span::styled(" ·", Style::default().fg(theme.muted)));
            }
            status_line.push(Span::styled(
                format!(" {status}"),
                Style::default().fg(color),
            ));
            status_line.push(Span::styled(
                format!("  {changes}"),
                Style::default().fg(theme.muted),
            ));
            ListItem::new(vec![
                Line::from(vec![
                    Span::styled(format!(" {name}"), Style::default().fg(theme.text).bold()),
                    Span::styled(format!("  {branch}"), Style::default().fg(theme.muted)),
                ]),
                Line::from(status_line),
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
            if let Some(snapshot) = &report.snapshot {
                lines.push(Line::styled(
                    snapshot.worktree_status(),
                    Style::default().fg(theme.worktree(snapshot)).bold(),
                ));
            }
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
                Span::styled("Tab ", Style::default().fg(theme.mint)),
                Span::raw("details  "),
                Span::styled("r ", Style::default().fg(theme.mint)),
                Span::raw("refresh  "),
                Span::styled("m ", Style::default().fg(theme.mint)),
                Span::raw("draft  "),
                Span::styled("a ", Style::default().fg(theme.mint)),
                Span::raw("AI  "),
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

fn models_view(frame: &mut Frame, app: &App, theme: Theme) {
    let models = app.models.as_ref().unwrap();
    let bounds = frame.area();
    let width = bounds.width.saturating_sub(4).min(100);
    let height = bounds.height.saturating_sub(2).min(20);
    let area = Rect::new(
        bounds.x + (bounds.width - width) / 2,
        bounds.y + (bounds.height - height) / 2,
        width,
        height,
    );
    frame.render_widget(Clear, area);
    let vertical_padding = u16::from(bounds.height >= 20);
    let block = theme
        .block(" AI MODEL LIBRARY ", true)
        .padding(Padding::new(1, 1, vertical_padding, vertical_padding));
    let inner = block.inner(area);
    frame.render_widget(block, area);
    let [choices, _, info, _, body, _, footer] = Layout::vertical([
        Constraint::Length(models.choices.len().min(2) as u16),
        Constraint::Length(1),
        Constraint::Length(3),
        Constraint::Length(1),
        Constraint::Min(3),
        Constraint::Length(1),
        Constraint::Length(2),
    ])
    .areas(inner);
    let rows: Vec<_> = models
        .choices
        .iter()
        .enumerate()
        .map(|(index, (name, path))| {
            let marker = if index == models.selected {
                "› "
            } else {
                "  "
            };
            let status = if path.as_ref().is_some_and(|path| path.is_file()) {
                " [present]"
            } else {
                " [not installed]"
            };
            ListItem::new(format!("{marker}{name}{status}")).style(if index == models.selected {
                Style::default().fg(theme.text).bg(theme.selected).bold()
            } else {
                Style::default().fg(theme.muted)
            })
        })
        .collect();
    frame.render_widget(List::new(rows), choices);
    frame.render_widget(
        Paragraph::new(vec![
            Line::from("2.74GB model · ~5.5GB cache · CPU / 2 threads"),
            Line::from("Unsloth · Apache-2.0 · experimental drafts"),
            Line::from(if crate::assets::RELEASE_PUBLISHED {
                "GitHub Release · source stays local"
            } else {
                "Release pending: part01 upload needs approval"
            }),
        ])
        .style(Style::default().fg(theme.muted)),
        info,
    );
    match models.phase {
        ModelPhase::Busy => {
            if let Some(progress) = &models.progress {
                let [status, bar, details] = Layout::vertical([
                    Constraint::Length(1),
                    Constraint::Length(1),
                    Constraint::Min(1),
                ])
                .areas(body);
                let phase = match progress.phase {
                    crate::assets::Phase::Downloading => "Downloading",
                    crate::assets::Phase::Verifying if body.width < 60 => "Local SHA-256",
                    crate::assets::Phase::Verifying => "Checking local SHA-256",
                    crate::assets::Phase::Assembling => "Assembling GGUF",
                };
                frame.render_widget(
                    Paragraph::new(format!("{phase} · {}", progress.label)),
                    status,
                );
                let ratio = if progress.total == 0 {
                    0.
                } else {
                    (progress.bytes as f64 / progress.total as f64).clamp(0., 1.)
                };
                frame.render_widget(
                    Gauge::default()
                        .gauge_style(Style::default().fg(theme.mint).bg(theme.border))
                        .ratio(ratio)
                        .label(format!("{:.1}%", ratio * 100.))
                        .use_unicode(true),
                    bar,
                );
                let rate = if progress.bytes_per_second > 0. {
                    format!(
                        " · {:.1}MiB/s · ~{}s remaining",
                        progress.bytes_per_second / 1048576.,
                        ((progress.total.saturating_sub(progress.bytes)) as f64
                            / progress.bytes_per_second)
                            .ceil() as u64
                    )
                } else {
                    String::new()
                };
                frame.render_widget(
                    Paragraph::new(format!(
                        "{:.1} / {:.1}MiB{rate}",
                        progress.bytes as f64 / 1048576.,
                        progress.total as f64 / 1048576.
                    ))
                    .wrap(Wrap { trim: false }),
                    details,
                );
            } else {
                frame.render_widget(Paragraph::new("Preparing local model operation…"), body);
            }
        }
        ModelPhase::Confirm => {
            frame.render_widget(Paragraph::new("Download 2.74GB from GitHub?\n~7.5GB free disk required; parts/licenses cached.\nNo model/code executes.").wrap(Wrap {trim:false}),body);
        }
        ModelPhase::Ready => {
            frame.render_widget(Paragraph::new("Model SHA-256 verified and selected.\nPython3.11+ and llama-server b11429 required.\nNo inference started.").wrap(Wrap {trim:false}).style(Style::default().fg(theme.mint)),body);
        }
        ModelPhase::Error => {
            frame.render_widget(
                Paragraph::new(safe(&models.error))
                    .wrap(Wrap { trim: false })
                    .style(Style::default().fg(theme.red)),
                body,
            );
        }
        ModelPhase::Browse => {
            frame.render_widget(Paragraph::new("Select a model/source.\nEnter checks a local file or opens confirmation.\nD opens download confirmation.").wrap(Wrap {trim:false}),body);
        }
    }
    frame.render_widget(
        Paragraph::new(match models.phase {
            ModelPhase::Busy => "Esc cancels · partials preserved · q/Ctrl+C exit",
            ModelPhase::Ready => "Enter/Esc return · m drafts on dashboard · q quit",
            ModelPhase::Confirm => "Enter/D confirm · Esc back · q quit",
            ModelPhase::Error => "↑↓ select · Enter retry · D download · Esc close · q quit",
            ModelPhase::Browse => "↑↓ select · Enter use · D download · Esc close · q quit",
        })
        .wrap(Wrap { trim: false })
        .style(Style::default().fg(theme.muted)),
        footer,
    );
}

fn draft_view(frame: &mut Frame, app: &App, theme: Theme) {
    let dialog = app.draft.as_ref().unwrap();
    let bounds = frame.area();
    let width = bounds.width.saturating_sub(4).min(100);
    let height = bounds.height.saturating_sub(2).min(18);
    let area = Rect::new(
        bounds.x + (bounds.width - width) / 2,
        bounds.y + (bounds.height - height) / 2,
        width,
        height,
    );
    frame.render_widget(Clear, area);
    // Keep all capacity rows visible at 60x18; add a top/bottom inset where room permits.
    let vertical_padding = u16::from(bounds.height >= 20);
    let block = theme
        .block(" LOCAL COMMIT DRAFT ", true)
        .padding(Padding::new(1, 1, vertical_padding, vertical_padding));
    let inner = block.inner(area);
    frame.render_widget(block, area);
    let [header, _, body, _, footer] = Layout::vertical([
        Constraint::Length(3),
        Constraint::Length(1),
        Constraint::Min(5),
        Constraint::Length(1),
        Constraint::Length(2),
    ])
    .areas(inner);
    let count = dialog
        .input
        .as_ref()
        .map(|input| {
            format!(
                " · {} files · {:.1}KiB",
                input.files,
                input.diff.len() as f64 / 1024.
            )
        })
        .unwrap_or_default();
    frame.render_widget(
        Paragraph::new(vec![
            Line::styled(
                format!("Staged changes only{count}"),
                Style::default().fg(theme.muted),
            ),
            Line::styled(
                safe(dialog.path.to_string_lossy()),
                Style::default().fg(theme.muted),
            ),
            Line::styled(
                "Unstaged/untracked excluded.",
                Style::default().fg(theme.muted),
            ),
        ]),
        header,
    );
    let (text, title) = match dialog.phase {
        DraftPhase::Generating => ("Preparing CPU draft…".to_string(), " Working ".to_string()),
        DraftPhase::Capacity => {
            let capacity = dialog.capacity.as_ref().unwrap();
            let text=format!("Prompt {} + {} output = {} tokens.\nCurrent context: {}.\n{}",capacity.prompt_tokens,capacity.output_tokens,capacity.prompt_tokens+capacity.output_tokens,capacity.context,match capacity.suggested_context {
                Some(context)=>format!("Required context: {context}.\nMore RAM/time; speed/accuracy unverified.\nNothing omitted."),
                None=>"Above maximum 262144. Reduce staged scope manually.\nNothing omitted; no generation started.".into(),
            });
            (text, " Complete-input capacity ".into())
        }
        DraftPhase::Checking => (
            dialog.text.clone(),
            " Checking staged changes / HEAD… ".into(),
        ),
        DraftPhase::Editing => (
            dialog.text.clone(),
            format!(" English subject · {} / 72 ", dialog.text.chars().count()),
        ),
        DraftPhase::Reviewed => (
            dialog.text.clone(),
            " Reviewed subject · copy manually ".into(),
        ),
        DraftPhase::Error => (safe(&dialog.error), " Draft unavailable ".into()),
    };
    frame.render_widget(
        Paragraph::new(text).wrap(Wrap { trim: false }).block(
            theme
                .block("", false)
                .padding(Padding::horizontal(1))
                .title(Line::styled(title, Style::default().fg(theme.text))),
        ),
        body,
    );
    let instruction = match dialog.phase {
        DraftPhase::Editing => "Type / Backspace · Ctrl+U clear · Enter recheck · Esc close",
        DraftPhase::Reviewed => "Point-in-time check · NOT committed · Esc close",
        DraftPhase::Error => "Esc close · m retries from dashboard",
        DraftPhase::Capacity
            if dialog
                .capacity
                .as_ref()
                .unwrap()
                .suggested_context
                .is_some() =>
        {
            "Enter approve larger context · Esc cancel"
        }
        DraftPhase::Capacity => "Esc close · reduce staged scope manually",
        _ => "Esc cancel · Ctrl+C exit",
    };
    frame.render_widget(
        Paragraph::new(
            if dialog.phase == DraftPhase::Editing && !dialog.error.is_empty() {
                safe(&dialog.error)
            } else {
                instruction.into()
            },
        )
        .wrap(Wrap { trim: false })
        .style(Style::default().fg(theme.muted)),
        footer,
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
    fn draft_hierarchy_insets_and_error_spacing_are_clear() {
        for color in [true, false] {
            for (width, height) in [(140, 36), (80, 24), (60, 18)] {
                let mut app = App::new(false, color, Duration::from_secs(10));
                let mut dialog = crate::ui::DraftDialog::new("/repo".into());
                dialog.phase = DraftPhase::Error;
                dialog.error = "No staged changes. Stage changes yourself, then press m.".into();
                app.draft = Some(dialog);
                let mut terminal = Terminal::new(TestBackend::new(width, height)).unwrap();
                terminal.draw(|frame| draw(frame, &mut app)).unwrap();
                let buffer = terminal.backend().buffer();
                let rows: Vec<String> = buffer
                    .content
                    .chunks(width as usize)
                    .map(|row| row.iter().map(|cell| cell.symbol()).collect())
                    .collect();
                let locate = |label: &str| {
                    rows.iter()
                        .enumerate()
                        .find_map(|(y, row)| {
                            row.find(label).map(|byte| (row[..byte].chars().count(), y))
                        })
                        .unwrap_or_else(|| panic!("Missing {label} at {width}x{height}"))
                };
                let (title_x, title_y) = locate("LOCAL COMMIT DRAFT");
                let (scope_x, scope_y) = locate("Staged changes only");
                let (_, excluded_y) = locate("Unstaged/untracked excluded.");
                let (error_x, error_y) = locate("Draft unavailable");
                let (message_x, _) = locate("No staged changes.");
                assert_eq!(
                    message_x,
                    scope_x + 2,
                    "Body message needs an inset from its border"
                );
                let cell = |x, y| &buffer.content[y * width as usize + x];
                let theme = Theme::new(color);
                assert!(cell(title_x, title_y).modifier.contains(Modifier::BOLD));
                assert_eq!(cell(title_x, title_y).fg, theme.mint);
                assert!(!cell(scope_x, scope_y).modifier.contains(Modifier::BOLD));
                assert_eq!(cell(scope_x, scope_y).fg, theme.muted);
                assert_eq!(cell(error_x, error_y).fg, theme.text);
                let modal_width = width.saturating_sub(4).min(100) as usize;
                let left = (width as usize - modal_width) / 2;
                assert!(scope_x >= left + 2, "Header needs a horizontal inset");
                assert!(
                    error_y > excluded_y + 1,
                    "Error box needs separation from scope"
                );
                if height >= 20 {
                    assert!(scope_y > title_y + 1, "Roomy terminals need a top inset");
                }
                for y in excluded_y + 1..error_y {
                    for x in left + 1..left + modal_width - 1 {
                        assert_eq!(cell(x, y).symbol(), " ", "Expected blank separator row");
                    }
                }
                assert!(!rows.join("\n").contains("Review wording"));
                assert!(rows.join("\n").contains("Esc close"));
            }
        }
    }

    #[test]
    fn modals_dim_only_background_and_restore_it_on_close() {
        for color in [true, false] {
            for (width, height) in [(140, 36), (80, 24), (60, 18)] {
                let mut app = App::new(false, color, Duration::from_secs(10));
                app.receive(Update::Started {
                    paths: vec!["/projects/ui-fixture".into()],
                    warnings: vec![],
                });
                let mut terminal = Terminal::new(TestBackend::new(width, height)).unwrap();
                terminal.draw(|frame| draw(frame, &mut app)).unwrap();
                let normal = terminal.backend().buffer().clone();
                for phase in [
                    DraftPhase::Generating,
                    DraftPhase::Capacity,
                    DraftPhase::Editing,
                    DraftPhase::Checking,
                    DraftPhase::Reviewed,
                    DraftPhase::Error,
                ] {
                    let mut dialog = crate::ui::DraftDialog::new("/repo".into());
                    dialog.phase = phase;
                    dialog.capacity = Some(crate::draft::Capacity {
                        diff_bytes: 300000,
                        diff_tokens: 2000,
                        prompt_tokens: 6000,
                        output_tokens: 192,
                        context: 4096,
                        suggested_context: Some(8192),
                    });
                    app.draft = Some(dialog);
                    terminal.draw(|frame| draw(frame, &mut app)).unwrap();
                    assert_modal_layers(terminal.backend().buffer(), color, 18);
                }
                app.draft = None;
                for phase in [
                    ModelPhase::Browse,
                    ModelPhase::Confirm,
                    ModelPhase::Busy,
                    ModelPhase::Ready,
                    ModelPhase::Error,
                ] {
                    let mut models = crate::ui::ModelManager::new(None);
                    models.phase = phase;
                    app.models = Some(models);
                    terminal.draw(|frame| draw(frame, &mut app)).unwrap();
                    assert_modal_layers(terminal.backend().buffer(), color, 20);
                }
                app.models = None;
                terminal.draw(|frame| draw(frame, &mut app)).unwrap();
                assert_eq!(
                    terminal.backend().buffer(),
                    &normal,
                    "Closing must restore the dashboard"
                );
            }
        }
    }

    fn assert_modal_layers(buffer: &ratatui::buffer::Buffer, color: bool, max_height: u16) {
        let bounds = buffer.area;
        let width = bounds.width.saturating_sub(4).min(100);
        let height = bounds.height.saturating_sub(2).min(max_height);
        let left = (bounds.width - width) / 2;
        let top = (bounds.height - height) / 2;
        for (index, cell) in buffer.content.iter().enumerate() {
            let x = index as u16 % bounds.width;
            let y = index as u16 / bounds.width;
            if (left..left + width).contains(&x) && (top..top + height).contains(&y) {
                assert!(
                    !cell.modifier.contains(Modifier::DIM),
                    "Modal must not inherit dimming"
                );
            } else {
                assert!(
                    cell.modifier.contains(Modifier::DIM),
                    "Background must be dimmed"
                );
                assert!(
                    !cell
                        .modifier
                        .intersects(Modifier::BOLD | Modifier::REVERSED)
                );
                assert_eq!(cell.fg, Theme::new(color).muted);
                assert_eq!(cell.bg, Theme::new(color).bg);
            }
        }
    }

    #[test]
    fn all_model_phases_keep_insets_consent_metadata_and_controls_visible() {
        let file = tempfile::NamedTempFile::new().unwrap();
        for color in [true, false] {
            for (width, height) in [(140, 36), (80, 24), (60, 18)] {
                for phase in [
                    ModelPhase::Browse,
                    ModelPhase::Confirm,
                    ModelPhase::Busy,
                    ModelPhase::Ready,
                    ModelPhase::Error,
                ] {
                    let mut app = App::new(false, color, Duration::from_secs(10));
                    let mut models = crate::ui::ModelManager::new(Some(file.path().into()));
                    models.phase = phase;
                    models.choices[0].1 = None; // Isolate from the user's real cache.
                    models.error = "Fixture error\x1b[2J".into();
                    app.models = Some(models);
                    let mut terminal = Terminal::new(TestBackend::new(width, height)).unwrap();
                    terminal.draw(|frame| draw(frame, &mut app)).unwrap();
                    let buffer = terminal.backend().buffer();
                    let rows: Vec<String> = buffer
                        .content
                        .chunks(width as usize)
                        .map(|row| row.iter().map(|cell| cell.symbol()).collect())
                        .collect();
                    let text = rows.join("\n");
                    let locate = |label: &str| {
                        rows.iter()
                            .enumerate()
                            .find_map(|(y, row)| {
                                row.find(label).map(|byte| (row[..byte].chars().count(), y))
                            })
                            .unwrap_or_else(|| {
                                panic!("Missing {label} at {width}x{height}: {text}")
                            })
                    };
                    let (title_x, title_y) = locate("AI MODEL LIBRARY");
                    let (choice_x, choice_y) = locate("Existing file · pinned Qwen3.5");
                    let (_, source_y) = locate("GitHub Release · source stays local");
                    let (meta_x, meta_y) = locate("Unsloth · Apache-2.0 · experimental drafts");
                    assert!(text.contains("[not installed]") && text.contains("[present]"));
                    let theme = Theme::new(color);
                    let cell = |x, y| &buffer.content[y * width as usize + x];
                    assert!(cell(title_x, title_y).modifier.contains(Modifier::BOLD));
                    assert_eq!(cell(title_x, title_y).fg, theme.mint);
                    assert_eq!(cell(choice_x, choice_y).fg, theme.text);
                    assert_eq!(cell(choice_x, choice_y).bg, theme.selected);
                    assert!(!cell(meta_x, meta_y).modifier.contains(Modifier::BOLD));
                    assert_eq!(cell(meta_x, meta_y).fg, theme.muted);
                    let first_choice_y = choice_y - 1;
                    let left = (width - width.saturating_sub(4).min(100)) / 2;
                    assert!(choice_x >= left as usize + 2);
                    if height >= 20 {
                        assert!(first_choice_y > title_y + 1);
                    }
                    let (body_y, required): (usize, &[&str]) = match phase {
                        ModelPhase::Browse => (
                            locate("Select a model/source.").1,
                            &[
                                "Enter checks a local file",
                                "D opens download confirmation.",
                                "Esc close",
                            ],
                        ),
                        ModelPhase::Confirm => (
                            locate("Download 2.74GB from GitHub?").1,
                            &[
                                "~7.5GB free disk required",
                                "parts/licenses cached.",
                                "No model/code executes.",
                                "Enter/D confirm",
                                "Esc back",
                            ],
                        ),
                        ModelPhase::Busy => (
                            locate("Preparing local model operation").1,
                            &["Esc cancels", "partials preserved"],
                        ),
                        ModelPhase::Ready => (
                            locate("Model SHA-256 verified and selected.").1,
                            &[
                                "Python3.11+",
                                "llama-server b11429",
                                "No inference started.",
                                "Enter/Esc return",
                            ],
                        ),
                        ModelPhase::Error => {
                            (locate("Fixture error").1, &["Esc close", "Enter retry"])
                        }
                    };
                    assert!(
                        body_y > source_y + 1,
                        "Body needs a blank separation from metadata"
                    );
                    for required in required {
                        assert!(text.contains(required), "Missing {required}: {text}");
                    }
                    assert!(!text.contains('\x1b'));
                    assert_modal_layers(buffer, color, 20);
                }
            }
        }
    }

    #[test]
    fn model_library_progress_is_bounded_and_reports_real_byte_phase() {
        for (width, height) in [(140, 36), (80, 24), (60, 18)] {
            let mut app = App::new(false, true, Duration::from_secs(10));
            let mut models = crate::ui::ModelManager::new(None);
            models.phase = ModelPhase::Busy;
            models.progress = Some(crate::assets::Progress {
                phase: crate::assets::Phase::Downloading,
                label: "fixture part01".into(),
                bytes: 50,
                total: 100,
                bytes_per_second: 5.,
            });
            app.models = Some(models);
            let mut terminal = Terminal::new(TestBackend::new(width, height)).unwrap();
            terminal.draw(|frame| draw(frame, &mut app)).unwrap();
            let text: String = terminal
                .backend()
                .buffer()
                .content
                .iter()
                .map(|cell| cell.symbol())
                .collect();
            assert!(text.contains("AI MODEL LIBRARY"));
            assert!(text.contains("50.0%"));
            assert!(text.contains("Downloading"));
            assert!(text.contains("Esc cancels"));
        }
    }

    #[test]
    fn every_asset_progress_phase_keeps_gauge_bytes_rate_and_eta_visible() {
        for (width, height) in [(140, 36), (80, 24), (60, 18)] {
            for (phase, label) in [
                (crate::assets::Phase::Downloading, "Downloading"),
                (crate::assets::Phase::Verifying, "SHA-256"),
                (crate::assets::Phase::Assembling, "Assembling GGUF"),
            ] {
                let mut app = App::new(false, true, Duration::from_secs(10));
                let mut models = crate::ui::ModelManager::new(Some("/absent-fixture".into()));
                models.phase = ModelPhase::Busy;
                models.progress = Some(crate::assets::Progress {
                    phase,
                    label: "fixture part01".into(),
                    bytes: 50 * 1048576,
                    total: 100 * 1048576,
                    bytes_per_second: 5. * 1048576.,
                });
                app.models = Some(models);
                let mut terminal = Terminal::new(TestBackend::new(width, height)).unwrap();
                terminal.draw(|frame| draw(frame, &mut app)).unwrap();
                let text: String = terminal
                    .backend()
                    .buffer()
                    .content
                    .iter()
                    .map(|cell| cell.symbol())
                    .collect();
                for required in [
                    label,
                    "fixture part01",
                    "50.0%",
                    "50.0 / 100.0MiB",
                    "5.0MiB/s",
                    "~10s remaining",
                    "Esc cancels",
                ] {
                    assert!(
                        text.contains(required),
                        "Missing {required} at {width}x{height}: {text}"
                    );
                }
            }
        }
    }

    #[test]
    fn capacity_shows_exact_prompt_and_required_context_at_supported_sizes() {
        for (width, height) in [(140, 36), (80, 24), (60, 18)] {
            let mut app = App::new(false, false, Duration::from_secs(10));
            let mut dialog = crate::ui::DraftDialog::new("/repo".into());
            dialog.phase = DraftPhase::Capacity;
            dialog.capacity = Some(crate::draft::Capacity {
                diff_bytes: 300000,
                diff_tokens: 2000,
                prompt_tokens: 6000,
                output_tokens: 192,
                context: 4096,
                suggested_context: Some(8192),
            });
            app.draft = Some(dialog);
            let mut terminal = Terminal::new(TestBackend::new(width, height)).unwrap();
            terminal.draw(|frame| draw(frame, &mut app)).unwrap();
            let text: String = terminal
                .backend()
                .buffer()
                .content
                .iter()
                .map(|cell| cell.symbol())
                .collect();
            assert!(text.contains("Prompt 6000 + 192 output = 6192 tokens."));
            assert!(text.contains("Current context: 4096"));
            assert!(text.contains("Required context: 8192"));
            assert!(text.contains("More RAM/time; speed/accuracy unverified."));
            assert!(text.contains("Nothing omitted."));
            assert!(text.contains("Enter approve larger context"));
        }
    }
    #[test]
    fn context_above_maximum_never_offers_approval() {
        let mut app = App::new(false, true, Duration::from_secs(10));
        let mut dialog = crate::ui::DraftDialog::new("/repo".into());
        dialog.phase = DraftPhase::Capacity;
        dialog.capacity = Some(crate::draft::Capacity {
            diff_bytes: 300000,
            diff_tokens: 2000,
            prompt_tokens: 300000,
            output_tokens: 192,
            context: 262144,
            suggested_context: None,
        });
        app.draft = Some(dialog);
        let mut terminal = Terminal::new(TestBackend::new(60, 18)).unwrap();
        terminal.draw(|frame| draw(frame, &mut app)).unwrap();
        let text: String = terminal
            .backend()
            .buffer()
            .content
            .iter()
            .map(|cell| cell.symbol())
            .collect();
        assert!(text.contains("Above maximum 262144"));
        assert!(text.contains("Nothing omitted; no generation started."));
        assert!(text.contains("reduce staged scope manually"));
        assert!(!text.contains("Enter approve"));
    }

    #[test]
    fn draft_overlay_shows_scope_subject_and_safe_errors_at_supported_sizes() {
        for (width, height) in [(140, 36), (80, 24), (60, 18)] {
            let mut app = App::new(false, false, Duration::from_secs(10));
            let mut dialog = super::super::DraftDialog::new("/repo".into());
            dialog.phase = DraftPhase::Editing;
            dialog.text = "Add the staged answer constant".into();
            app.draft = Some(dialog);
            let mut terminal = Terminal::new(TestBackend::new(width, height)).unwrap();
            terminal.draw(|frame| draw(frame, &mut app)).unwrap();
            let text: String = terminal
                .backend()
                .buffer()
                .content
                .iter()
                .map(|cell| cell.symbol())
                .collect();
            assert!(text.contains("Staged changes only"));
            assert!(text.contains("Add the staged answer constant"));
            assert!(text.contains("Unstaged/untracked"));
            assert!(text.contains("Enter recheck"));
            app.draft.as_mut().unwrap().phase = DraftPhase::Error;
            app.draft.as_mut().unwrap().error = "No model\x1b[2J".into();
            terminal.draw(|frame| draw(frame, &mut app)).unwrap();
            let text: String = terminal
                .backend()
                .buffer()
                .content
                .iter()
                .map(|cell| cell.symbol())
                .collect();
            assert!(!text.contains('\x1b'));
        }
    }

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
    fn synced_branch_with_uncommitted_files_is_prominent_at_every_supported_width() {
        for (width, height) in [(140, 36), (80, 24), (60, 18)] {
            let mut app = App::new(false, true, Duration::from_secs(10));
            let path = "/projects/dirty-repo".into();
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
                    staged: 1,
                    modified: 1,
                    untracked: 1,
                    changed: 3,
                    ..Snapshot::default()
                }),
                verification: Verification::Cached,
                error: None,
            }));
            assert_eq!(
                app.entries[0].report.as_ref().unwrap().state(),
                State::Synced
            );
            let mut terminal = Terminal::new(TestBackend::new(width, height)).unwrap();
            terminal.draw(|frame| draw(frame, &mut app)).unwrap();
            let buffer = terminal.backend().buffer();
            let text: String = buffer.content.iter().map(|c| c.symbol()).collect();
            assert!(
                text.contains("3 uncommitted"),
                "Missing dirty-worktree warning at {width}x{height}: {text}"
            );
            assert!(
                text.contains("In sync"),
                "Branch synchronization should still be visible"
            );
            let amber = Theme::new(true).amber;
            assert!(
                buffer
                    .content
                    .iter()
                    .any(|c| c.symbol() == "3" && c.fg == amber),
                "Dirty work must not look green"
            );
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
