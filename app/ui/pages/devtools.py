"""Geliştirici araçları: dil seçimi ve otomatik zincir."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QGridLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from ...core.tasks import Task
from ...modules import catalog as catalog_mod
from ...modules import devtools, installer
from ...core.i18n import t, tn
from .. import theme
from ..widgets import Badge, Card, Hint, SectionTitle, TitleLabel
from .base import BasePage


class DevToolsPage(BasePage):
    step_id = "devtools"
    title = "Geliştirici araçları"
    subtitle = "Dil seçin; gerekli programlar, VS Code eklentileri ve ilk ayarlar otomatik hazırlanır."

    def __init__(self, session, parent=None):
        super().__init__(session, parent)
        self.languages = devtools.load_languages()
        self.catalog = catalog_mod.load_catalog()
        self.lang_checks: dict[str, QCheckBox] = {}
        self._build()
        self._restore()

    def _build(self) -> None:
        card = Card()
        row = QHBoxLayout()
        texts = QVBoxLayout()
        texts.setSpacing(2)
        texts.addWidget(TitleLabel("Hangi dilleri kullanıyorsunuz?", 13))
        texts.addWidget(Hint("Seçtiğiniz dil için editör, eklenti ve çalışma zamanı birlikte kurulur."))
        row.addLayout(texts, 1)

        self.vscode_always = QCheckBox("VS Code her zaman kurulsun")
        self.vscode_always.setChecked(True)
        row.addWidget(self.vscode_always)
        card.add_layout(row)
        self.add(card)

        grid = QGridLayout()
        grid.setSpacing(10)
        for index, language in enumerate(self.languages):
            lang_card = Card()
            top = QHBoxLayout()
            top.setSpacing(8)
            checkbox = QCheckBox()
            self.lang_checks[language.id] = checkbox
            top.addWidget(checkbox, 0, Qt.AlignmentFlag.AlignTop)

            title = QLabel(f"{language.icon}  {language.title}")
            title.setObjectName("CardTitle")
            top.addWidget(title, 1)
            lang_card.add_layout(top)

            desc = Hint(language.description)
            lang_card.add(desc)

            if language.apps or language.extensions:
                chips = QHBoxLayout()
                chips.setSpacing(4)
                chips.addWidget(Badge(t("{count} program", count=len(language.apps)), "muted"))
                if language.extensions:
                    chips.addWidget(Badge(t("{count} eklenti", count=len(language.extensions)), "info"))
                chips.addStretch(1)
                lang_card.add_layout(chips)

            checkbox.stateChanged.connect(lambda _: self._update_summary())
            grid.addWidget(lang_card, index // 3, index % 3)

        for column in range(3):
            grid.setColumnStretch(column, 1)
        self.add_layout(grid)

        self.info_card = Card()
        self.info_card.add(SectionTitle("SEÇİLECEKLER"))
        self.info_label = QLabel("henüz dil seçilmedi")
        self.info_label.setObjectName("Hint")
        self.info_label.setWordWrap(True)
        self.info_card.add(self.info_label)
        self.add(self.info_card)
        self.add_stretch()

    def _update_summary(self) -> None:
        selected = self.selected_languages()
        if not selected:
            self.info_label.setText("henüz dil seçilmedi")
            return
        parts = []
        for language in selected:
            apps = [self._app_name(a) for a in language.apps]
            parts.append(f"{language.title}: " + (", ".join(apps) if apps else "program yok") +
                         (f" + {len(language.extensions)} eklenti" if language.extensions else ""))
        if self.vscode_always.isChecked():
            parts.append("VS Code")
        self.info_label.setText("\n".join(parts))

    def _app_name(self, app_id: str) -> str:
        app = self.catalog.by_id(app_id)
        return app.name if app else app_id

    def selected_languages(self) -> list[devtools.Language]:
        return [l for l in self.languages if self.lang_checks.get(l.id) and self.lang_checks[l.id].isChecked()]

    # ---------------------------------------------------------------- state
    def _restore(self) -> None:
        saved = set(self.session.get("devlangs") or [])
        for lang_id, checkbox in self.lang_checks.items():
            if lang_id in saved:
                checkbox.setChecked(True)
        self._update_summary()

    def collect(self) -> None:
        self.session.set("devlangs", [l.id for l in self.selected_languages()])

    def plan(self) -> list[Task]:
        languages = self.selected_languages()
        if not languages and not self.vscode_always.isChecked():
            return []

        tasks: list[Task] = []

        # 1) Programlar
        wanted: list[catalog_mod.CatalogApp] = []
        if self.vscode_always.isChecked() or languages:
            vscode = self.catalog.by_id("vscode")
            if vscode:
                wanted.append(vscode)
        for language in languages:
            for app_id in language.apps:
                app = self.catalog.by_id(app_id)
                if app and app not in wanted:
                    wanted.append(app)

        for app in wanted:
            def make(app=app):
                def run(ctx):
                    result = installer.install(app, dry_run=ctx.dry_run, on_line=ctx.log)
                    if result.status == "failed":
                        raise RuntimeError(result.message)
                    ctx.add("dev_apps", 1)
                return run

            tasks.append(Task(
                key=f"install:{app.id}",
                group="Geliştirici · programlar",
                title=app.name,
                fn=make(),
                weight=max(1.0, app.size_mb / 80.0),
            ))

        # 2) VS Code eklentileri
        extensions: list[str] = []
        for language in languages:
            for ext in language.extensions:
                if ext not in extensions:
                    extensions.append(ext)

        if extensions:
            def run_ext(ctx):
                installer.refresh_path()
                ok, fail = devtools.install_extensions(extensions, ctx.dry_run, on_line=ctx.log)
                ctx.add("dev_extensions", ok)
                if fail and not ok:
                    raise RuntimeError("eklentiler kurulamadı")

            tasks.append(Task(
                key="dev:extensions",
                group="Geliştirici · eklentiler",
                title=f"{len(extensions)} VS Code eklentisi",
                fn=run_ext,
                weight=2,
            ))

        # 3) Kurulum sonrası komutlar
        posts: list[str] = []
        for language in languages:
            for command in language.post:
                if command not in posts:
                    posts.append(command)

        if posts:
            def run_post(ctx):
                installer.refresh_path()
                ok, fail = devtools.run_post_commands(posts, ctx.dry_run, on_line=ctx.log)
                ctx.add("dev_post", ok)

            tasks.append(Task(
                key="dev:post",
                group="Geliştirici · ayarlar",
                title=", ".join(posts)[:60],
                fn=run_post,
                weight=2,
            ))

        return tasks

    def summary(self) -> str:
        count = len(self.selected_languages())
        return f"{count} dil" if count else "seçim yok"
