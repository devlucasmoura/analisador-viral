import threading
from tkinter import messagebox

import customtkinter as ctk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from src import config, license_manager
from src.analyzer import ChannelAnalysis, analyze_channel
from src.visualizer import create_metrics_figure
from src.youtube_client import YouTubeClient, YouTubeError


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

WINDOW_TITLE = "Analisador Viral"
WINDOW_SIZE = "1100x750"


class LicenseScreen(ctk.CTkFrame):
    def __init__(self, master, on_success):
        super().__init__(master)
        self.on_success = on_success

        container = ctk.CTkFrame(self, fg_color="transparent")
        container.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(
            container, text="Analisador Viral",
            font=ctk.CTkFont(size=32, weight="bold"),
        ).pack(pady=(0, 8))
        ctk.CTkLabel(
            container, text="Cole a chave de acesso que você recebeu",
            font=ctk.CTkFont(size=13),
            text_color="gray70",
        ).pack(pady=(0, 20))

        self.entry = ctk.CTkEntry(
            container, width=460, height=44,
            placeholder_text="ANLV-XXXX-XXXX-XXXX-XXXX-XXXX-XXXX-XXXX",
            font=ctk.CTkFont(size=13),
        )
        self.entry.pack(pady=6)
        self.entry.bind("<Return>", lambda _: self._activate())

        self.status = ctk.CTkLabel(container, text="", text_color="#ff6b6b")
        self.status.pack(pady=(6, 6))

        ctk.CTkButton(
            container, text="Ativar chave",
            width=460, height=42, command=self._activate,
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(pady=6)

    def _activate(self):
        key = self.entry.get().strip()
        if not key:
            self.status.configure(text="Digite a chave.")
            return
        try:
            info = license_manager.activate_key(key)
        except ValueError as e:
            self.status.configure(text=f"Chave inválida: {e}")
            return
        self.on_success(info)


class ApiKeyScreen(ctk.CTkFrame):
    def __init__(self, master, on_success):
        super().__init__(master)
        self.on_success = on_success

        container = ctk.CTkFrame(self, fg_color="transparent")
        container.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(
            container, text="Configuração da API do YouTube",
            font=ctk.CTkFont(size=22, weight="bold"),
        ).pack(pady=(0, 8))
        ctk.CTkLabel(
            container,
            text=("Cole abaixo sua chave da YouTube Data API v3.\n"
                  "Gere gratuitamente em: console.cloud.google.com\n"
                  "(Serviços → APIs → YouTube Data API v3 → Ativar → Criar credencial)"),
            font=ctk.CTkFont(size=12),
            text_color="gray70",
            justify="center",
        ).pack(pady=(0, 20))

        self.entry = ctk.CTkEntry(
            container, width=520, height=44,
            placeholder_text="AIzaSy...",
            font=ctk.CTkFont(size=13),
        )
        self.entry.pack(pady=6)
        self.entry.bind("<Return>", lambda _: self._save())

        self.status = ctk.CTkLabel(container, text="", text_color="#ff6b6b")
        self.status.pack(pady=(6, 6))

        ctk.CTkButton(
            container, text="Salvar",
            width=520, height=42, command=self._save,
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(pady=6)

    def _save(self):
        key = self.entry.get().strip()
        if not key.startswith("AIza"):
            self.status.configure(text="A chave deve começar com 'AIza'.")
            return
        config.save_api_key(key)
        self.on_success()


class MainScreen(ctk.CTkFrame):
    def __init__(self, master, license_info):
        super().__init__(master)
        self.license_info = license_info
        self._build()

    def _build(self):
        header = ctk.CTkFrame(self, height=70, corner_radius=0)
        header.pack(fill="x")
        header.pack_propagate(False)

        ctk.CTkLabel(
            header, text="Analisador Viral",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).pack(side="left", padx=20)

        license_text = f"Licença: {self.license_info.days_remaining} dia(s) restantes  •  expira {self.license_info.expires_on.strftime('%d/%m/%Y')}"
        ctk.CTkLabel(
            header, text=license_text,
            font=ctk.CTkFont(size=11), text_color="gray70",
        ).pack(side="right", padx=20)

        input_bar = ctk.CTkFrame(self, height=70, corner_radius=0, fg_color="#1f1f1f")
        input_bar.pack(fill="x")
        input_bar.pack_propagate(False)

        self.url_entry = ctk.CTkEntry(
            input_bar,
            placeholder_text="Cole o link do canal (ex: https://youtube.com/@MrBeast)",
            font=ctk.CTkFont(size=13), height=40,
        )
        self.url_entry.pack(side="left", padx=(20, 10), pady=15, fill="x", expand=True)
        self.url_entry.bind("<Return>", lambda _: self._analyze())

        self.analyze_btn = ctk.CTkButton(
            input_bar, text="Analisar", width=140, height=40,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._analyze,
        )
        self.analyze_btn.pack(side="right", padx=(0, 20), pady=15)

        self.status_label = ctk.CTkLabel(self, text="", text_color="gray70")
        self.status_label.pack(pady=6)

        self.content = ctk.CTkFrame(self, fg_color="transparent")
        self.content.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        self._show_welcome()

    def _show_welcome(self):
        for w in self.content.winfo_children():
            w.destroy()
        ctk.CTkLabel(
            self.content,
            text="Cole o link de um canal do YouTube acima e clique em Analisar",
            font=ctk.CTkFont(size=14), text_color="gray50",
        ).place(relx=0.5, rely=0.5, anchor="center")

    def _analyze(self):
        url = self.url_entry.get().strip()
        if not url:
            self.status_label.configure(text="Digite um link de canal.")
            return

        self.analyze_btn.configure(state="disabled", text="Analisando...")
        self.status_label.configure(text="Buscando dados no YouTube...")
        for w in self.content.winfo_children():
            w.destroy()

        threading.Thread(target=self._do_analysis, args=(url,), daemon=True).start()

    def _do_analysis(self, url: str):
        try:
            api_key = config.load_api_key()
            client = YouTubeClient(api_key)
            channel = client.analyze_channel(url, max_videos=10)
            analysis = analyze_channel(channel)
            self.after(0, lambda: self._render_results(analysis))
        except YouTubeError as e:
            self.after(0, lambda: self._show_error(str(e)))
        except Exception as e:
            self.after(0, lambda: self._show_error(f"Erro inesperado: {e}"))

    def _show_error(self, message: str):
        self.status_label.configure(text="")
        self.analyze_btn.configure(state="normal", text="Analisar")
        messagebox.showerror("Erro", message)
        self._show_welcome()

    def _render_results(self, analysis: ChannelAnalysis):
        self.status_label.configure(text="")
        self.analyze_btn.configure(state="normal", text="Analisar")

        for w in self.content.winfo_children():
            w.destroy()

        header = ctk.CTkFrame(self.content, fg_color="#1f1f1f", corner_radius=10)
        header.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(
            header, text=analysis.channel.title,
            font=ctk.CTkFont(size=18, weight="bold"),
        ).pack(anchor="w", padx=15, pady=(10, 2))
        stats_text = (
            f"{_fmt_int(analysis.channel.subscribers)} inscritos  •  "
            f"{_fmt_int(analysis.channel.total_videos)} vídeos no total  •  "
            f"Mediana de views (10 últimos): {_fmt_int(analysis.median_views)}"
        )
        ctk.CTkLabel(header, text=stats_text, text_color="gray70").pack(anchor="w", padx=15, pady=(0, 10))

        body = ctk.CTkFrame(self.content, fg_color="transparent")
        body.pack(fill="both", expand=True)
        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=2)
        body.grid_rowconfigure(0, weight=1)

        chart_frame = ctk.CTkFrame(body, fg_color="#1a1a1a", corner_radius=10)
        chart_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        figure = create_metrics_figure(analysis)
        canvas = FigureCanvasTkAgg(figure, master=chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=8, pady=8)

        side = ctk.CTkFrame(body, fg_color="transparent")
        side.grid(row=0, column=1, sticky="nsew")

        reasons_frame = ctk.CTkFrame(side, fg_color="#1f1f1f", corner_radius=10)
        reasons_frame.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(
            reasons_frame, text="Por que o top viralizou?",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(anchor="w", padx=12, pady=(10, 6))

        ctk.CTkLabel(
            reasons_frame, text=analysis.reasons.summary,
            wraplength=340, justify="left", text_color="gray80",
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=12, pady=(0, 8))

        if analysis.reasons.factors:
            for factor in analysis.reasons.factors:
                ctk.CTkLabel(
                    reasons_frame, text=f"•  {factor}",
                    wraplength=340, justify="left",
                    font=ctk.CTkFont(size=11),
                ).pack(anchor="w", padx=12, pady=2)
        ctk.CTkLabel(reasons_frame, text="").pack(pady=4)

        list_frame = ctk.CTkScrollableFrame(side, fg_color="#1f1f1f", corner_radius=10,
                                            label_text="Top 10 vídeos (por viralidade)")
        list_frame.pack(fill="both", expand=True)

        for a in analysis.videos:
            item = ctk.CTkFrame(list_frame, fg_color="#242424", corner_radius=6)
            item.pack(fill="x", pady=3, padx=4)

            top_row = ctk.CTkFrame(item, fg_color="transparent")
            top_row.pack(fill="x", padx=8, pady=(6, 2))
            badge_color = "#e94560" if a.is_viral else "gray50"
            ctk.CTkLabel(
                top_row, text=f"#{a.rank}",
                text_color=badge_color,
                font=ctk.CTkFont(size=13, weight="bold"),
                width=30,
            ).pack(side="left")
            ctk.CTkLabel(
                top_row, text=a.video.title[:60] + ("..." if len(a.video.title) > 60 else ""),
                font=ctk.CTkFont(size=11),
                anchor="w", justify="left",
            ).pack(side="left", fill="x", expand=True)

            info = f"{_fmt_int(a.video.views)} views  •  {a.viral_score:.1f}x mediana  •  {a.engagement_rate:.1f}% engajamento"
            ctk.CTkLabel(
                item, text=info, text_color="gray60",
                font=ctk.CTkFont(size=10),
            ).pack(anchor="w", padx=42, pady=(0, 6))


def _fmt_int(n: int) -> str:
    return f"{n:,}".replace(",", ".")


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(WINDOW_TITLE)
        self.geometry(WINDOW_SIZE)
        self.minsize(900, 600)

        self.current_frame = None
        self._route()

    def _route(self):
        license_info = license_manager.current_license()

        if license_info is None or license_info.is_expired:
            self._show(LicenseScreen(self, on_success=self._on_license_activated))
            return

        api_key = config.load_api_key()
        if not api_key:
            self._show(ApiKeyScreen(self, on_success=self._route))
            return

        self._show(MainScreen(self, license_info))

    def _on_license_activated(self, info):
        self._route()

    def _show(self, frame):
        if self.current_frame is not None:
            self.current_frame.destroy()
        self.current_frame = frame
        frame.pack(fill="both", expand=True)


if __name__ == "__main__":
    App().mainloop()
