"""
Lista de Tarefas com Notificações Nativas do Windows
Interface redesenhada — tema escuro refinado, resolução 1100×750
Melhorias:
  - Fontes maiores e melhor legibilidade
  - Entrada rápida de data/hora (pickers inline)
  - Notificações no canto inferior esquerdo (overlay interno)
  - Dois tipos: agendada e cíclica, empilhadas (máx. 2)
  - Sem duplicidade de notificação aberta por tipo
  - Tarefa em destaque na notificação (fonte amarela grande)
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from calendar import monthcalendar

# ── Notificações nativas do Windows ──────────────────────────────────────────
try:
    from winotify import Notification as WinNotify, audio
    NOTIF_BACKEND = "winotify"
except ImportError:
    try:
        from win10toast import ToastNotifier
        _toaster = ToastNotifier()
        NOTIF_BACKEND = "win10toast"
    except ImportError:
        NOTIF_BACKEND = None

APP_ID = "ListaDeTarefas"

def notificar(titulo, mensagem, tipo="ciclica"):
    if NOTIF_BACKEND == "winotify":
        try:
            n = WinNotify(app_id=APP_ID, title=titulo, msg=mensagem, duration="short")
            if tipo == "agendada":
                n.set_audio(audio.Default, loop=False)
            n.show()
        except Exception:
            pass
    elif NOTIF_BACKEND == "win10toast":
        try:
            threading.Thread(
                target=lambda: _toaster.show_toast(titulo, mensagem, duration=5, threaded=False),
                daemon=True).start()
        except Exception:
            pass

# ── Paleta ────────────────────────────────────────────────────────────────────
BG          = "#1e1e2e"
BG2         = "#252538"
BG3         = "#2d2d45"
BORDA       = "#3a3a55"
BORDA2      = "#4a4a6a"
ACCENT      = "#7c6af7"
ACCENT_H    = "#6a5ae0"
ACCENT2     = "#e74c3c"
ACCENT2_H   = "#c0392b"
FG          = "#e2e2f0"
FG2         = "#8888aa"
FG3         = "#606080"
FG_OK       = "#4caf82"
FG_OK2      = "#3a9e6a"
FG_WARN     = "#f39c12"
COR_DIARIO  = "#3a6baf"
COR_SEMANAL = "#7a3faf"
COR_ALTA    = "#e74c3c"
COR_MEDIA   = "#f39c12"
COR_BAIXA   = "#4caf82"

PRIOR_ORD = {"Alta": 0, "Média": 1, "Baixa": 2}
DIAS_HIST = 30
SAVE_FILE = Path.home() / "tarefas_app.json"

# Fontes compactas
FNT_TITLE  = ("Segoe UI", 10, "bold")
FNT_BODY   = ("Segoe UI", 9)
FNT_BODY_B = ("Segoe UI", 9, "bold")
FNT_SMALL  = ("Segoe UI", 8)
FNT_SMALL_B= ("Segoe UI", 8, "bold")
FNT_MONO   = ("Consolas", 8)
FNT_HDR    = ("Segoe UI", 12, "bold")
FNT_ICON   = ("Segoe UI", 11)
FNT_BADGE  = ("Segoe UI", 8, "bold")

# Fontes para notificação popup
FNT_NOTIF_TITULO = ("Segoe UI", 10, "bold")
FNT_NOTIF_TAREFA = ("Segoe UI", 11, "bold")   # destaque amarelo
FNT_NOTIF_MSG    = ("Segoe UI", 9)

# ── Helpers ───────────────────────────────────────────────────────────────────
def agora():
    return datetime.now().strftime("%d/%m/%Y %H:%M")

def parse_dt(s):
    if not s:
        return None
    for fmt in ("%d/%m/%Y %H:%M", "%Y-%m-%dT%H:%M"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass
    return None

def purgar_hist(historico):
    limite = datetime.now() - timedelta(days=DIAS_HIST)
    return [h for h in historico if (parse_dt(h.get("criado_em", "")) or datetime.min) >= limite]

def nova_tarefa_dict(texto, prioridade="Média", repeticao="Sem repetição", notif_agendada=""):
    a = agora()
    return {
        "texto": texto, "concluida": False, "concluida_em": None, "criado_em": a,
        "repeticao": repeticao, "prioridade": prioridade,
        "notif_agendada": notif_agendada, "notif_disparada": False,
        "log": [{"evento": "Criada", "quando": a}], "subtarefas": [],
    }

def cor_prior(p):
    return {"Alta": COR_ALTA, "Média": COR_MEDIA, "Baixa": COR_BAIXA}.get(p, FG2)

def cor_rep(r):
    return {"Diariamente": COR_DIARIO, "Semanalmente": COR_SEMANAL}.get(r)

def icone_log(ev):
    return {"Criada": ("🕐", FG2), "Concluída": ("✅", FG_OK), "Reaberta": ("↩", FG_WARN),
            "Sub criada": ("🕐", FG2), "Sub concluída": ("✅", FG_OK),
            "Sub reaberta": ("↩", FG_WARN), "Sub removida": ("🗑", ACCENT2)}.get(ev, ("•", FG2))

def _badge(parent, texto, bg_cor, fg_cor="#ffffff"):
    tk.Label(parent, text=texto, bg=bg_cor, fg=fg_cor,
             font=FNT_BADGE, padx=8, pady=3).pack(side="left", padx=(0, 4))

def sep_line(parent, color=BORDA, pady=0):
    tk.Frame(parent, bg=color, height=1).pack(fill="x", pady=pady)

# ── ScrollFrame ───────────────────────────────────────────────────────────────
class ScrollFrame(tk.Frame):
    def __init__(self, parent, bg=BG, **kw):
        super().__init__(parent, bg=bg, **kw)
        self.canvas = tk.Canvas(self, bg=bg, bd=0, highlightthickness=0)
        self.sb = tk.Scrollbar(self, orient="vertical", command=self.canvas.yview,
                               bg=BG2, troughcolor=BG, activebackground=BORDA2, width=10,
                               relief="flat", bd=0)
        self.inner = tk.Frame(self.canvas, bg=bg)
        self._cw = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=self.sb.set)
        self.sb.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.inner.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(self._cw, width=e.width))
        self.canvas.bind_all("<MouseWheel>", self._scroll)

    def _scroll(self, e):
        try:
            self.canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
        except Exception:
            pass

    def clear(self):
        for w in self.inner.winfo_children():
            w.destroy()

# ── DateTimePicker rápido ────────────────────────────────────────────────────
class DateTimePicker(tk.Toplevel):
    """Picker de data/hora com calendário e spinners — entrada rápida."""
    def __init__(self, parent, callback, initial=None):
        super().__init__(parent)
        self.callback = callback
        self.title("Escolher Data e Hora")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.grab_set()

        now = initial or datetime.now()
        self._year  = tk.IntVar(value=now.year)
        self._month = tk.IntVar(value=now.month)
        self._day   = tk.IntVar(value=now.day)
        self._hour  = tk.IntVar(value=now.hour)
        self._min   = tk.IntVar(value=now.minute)
        self._sel_day = now.day

        self._build()
        # Centraliza perto do pai
        self.update_idletasks()
        px = parent.winfo_rootx() + parent.winfo_width()//2 - self.winfo_width()//2
        py = parent.winfo_rooty() + parent.winfo_height()//2 - self.winfo_height()//2
        self.geometry(f"+{px}+{py}")

    def _build(self):
        # Header
        tk.Frame(self, bg=ACCENT, height=3).pack(fill="x")
        tk.Label(self, text="📅  Selecionar Data e Hora", bg=BG, fg=FG,
                 font=FNT_BODY_B).pack(pady=(10, 4))

        # Navegação mês/ano
        nav = tk.Frame(self, bg=BG); nav.pack(padx=16)
        tk.Button(nav, text="◀", bg=BG3, fg=FG, relief="flat", bd=0, font=FNT_BODY_B,
                  cursor="hand2", activebackground=BORDA, command=self._prev_month).pack(side="left", ipadx=8, ipady=4)
        self._lbl_mes = tk.Label(nav, text="", bg=BG, fg=FG, font=FNT_BODY_B, width=18, anchor="center")
        self._lbl_mes.pack(side="left", padx=8)
        tk.Button(nav, text="▶", bg=BG3, fg=FG, relief="flat", bd=0, font=FNT_BODY_B,
                  cursor="hand2", activebackground=BORDA, command=self._next_month).pack(side="left", ipadx=8, ipady=4)

        # Cabeçalho dias da semana
        dias_hdr = tk.Frame(self, bg=BG); dias_hdr.pack(padx=16, pady=(8, 2))
        for d in ["Dom","Seg","Ter","Qua","Qui","Sex","Sáb"]:
            tk.Label(dias_hdr, text=d, bg=BG, fg=FG3, font=FNT_SMALL, width=4, anchor="center").pack(side="left")

        # Grade do calendário
        self._cal_frame = tk.Frame(self, bg=BG); self._cal_frame.pack(padx=16)

        # Hora
        time_f = tk.Frame(self, bg=BG2, highlightbackground=BORDA, highlightthickness=1)
        time_f.pack(fill="x", padx=16, pady=(10, 6))
        tk.Label(time_f, text="🕐  Hora:", bg=BG2, fg=FG2, font=FNT_SMALL_B).pack(side="left", padx=10, pady=8)
        # Horas
        tk.Spinbox(time_f, from_=0, to=23, textvariable=self._hour, width=3,
                   bg=BG3, fg=FG, font=("Segoe UI", 13, "bold"), relief="flat",
                   buttonbackground=BG3, highlightthickness=0, justify="center",
                   format="%02.0f").pack(side="left", ipady=4)
        tk.Label(time_f, text=":", bg=BG2, fg=FG, font=("Segoe UI", 15, "bold")).pack(side="left")
        # Minutos com botões rápidos
        tk.Spinbox(time_f, from_=0, to=59, textvariable=self._min, width=3,
                   bg=BG3, fg=FG, font=("Segoe UI", 13, "bold"), relief="flat",
                   buttonbackground=BG3, highlightthickness=0, justify="center",
                   format="%02.0f").pack(side="left", ipady=4)
        # Botões rápidos de minuto
        for m in [0, 15, 30, 45]:
            tk.Button(time_f, text=f":{m:02d}", bg=BG3, fg=FG2, relief="flat", bd=0,
                      font=("Segoe UI", 9), cursor="hand2", activebackground=BORDA,
                      command=lambda v=m: self._min.set(v)).pack(side="left", padx=2, ipadx=4, ipady=3)

        # Botões
        btn_f = tk.Frame(self, bg=BG); btn_f.pack(fill="x", padx=16, pady=(4, 12))
        tk.Button(btn_f, text="Agora", bg=BG3, fg=FG2, relief="flat", bd=0, font=FNT_SMALL,
                  cursor="hand2", activebackground=BORDA,
                  command=self._usar_agora).pack(side="left", ipadx=10, ipady=5)
        tk.Button(btn_f, text="Cancelar", bg=BG3, fg=FG2, relief="flat", bd=0, font=FNT_SMALL,
                  cursor="hand2", activebackground=BORDA,
                  command=self.destroy).pack(side="right", ipadx=10, ipady=5, padx=(4,0))
        tk.Button(btn_f, text="✔  Confirmar", bg=ACCENT, fg="#fff", relief="flat", bd=0, font=FNT_SMALL_B,
                  cursor="hand2", activebackground=ACCENT_H,
                  command=self._confirmar).pack(side="right", ipadx=10, ipady=5)

        self._render_cal()

    MESES = ["Janeiro","Fevereiro","Março","Abril","Maio","Junho",
             "Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"]

    def _render_cal(self):
        for w in self._cal_frame.winfo_children():
            w.destroy()
        y, m = self._year.get(), self._month.get()
        self._lbl_mes.config(text=f"{self.MESES[m-1]}  {y}")
        semanas = monthcalendar(y, m)
        # Garante que o dia selecionado existe no mês atual
        import calendar
        max_day = calendar.monthrange(y, m)[1]
        if self._sel_day > max_day:
            self._sel_day = max_day
        for semana in semanas:
            row = tk.Frame(self._cal_frame, bg=BG); row.pack()
            for dia in semana:
                if dia == 0:
                    tk.Label(row, text="", bg=BG, width=4, font=FNT_SMALL).pack(side="left")
                else:
                    ativo = dia == self._sel_day
                    bg_d  = ACCENT if ativo else BG3
                    fg_d  = "#fff" if ativo else FG
                    btn = tk.Button(row, text=str(dia), bg=bg_d, fg=fg_d, relief="flat", bd=0,
                                    font=FNT_SMALL_B if ativo else FNT_SMALL,
                                    width=4, cursor="hand2", activebackground=ACCENT_H,
                                    command=lambda d=dia: self._selecionar_dia(d))
                    btn.pack(side="left", pady=2)

    def _selecionar_dia(self, d):
        self._sel_day = d; self._day.set(d); self._render_cal()

    def _prev_month(self):
        m, y = self._month.get(), self._year.get()
        if m == 1: self._month.set(12); self._year.set(y - 1)
        else: self._month.set(m - 1)
        self._render_cal()

    def _next_month(self):
        m, y = self._month.get(), self._year.get()
        if m == 12: self._month.set(1); self._year.set(y + 1)
        else: self._month.set(m + 1)
        self._render_cal()

    def _usar_agora(self):
        n = datetime.now()
        self._year.set(n.year); self._month.set(n.month)
        self._sel_day = n.day; self._day.set(n.day)
        self._hour.set(n.hour); self._min.set(n.minute)
        self._render_cal()

    def _confirmar(self):
        try:
            hora = int(float(self._hour.get()))
            minu = int(float(self._min.get()))
            dt = datetime(self._year.get(), self._month.get(), self._sel_day, hora, minu)
            self.callback(dt.strftime("%d/%m/%Y %H:%M"))
            self.destroy()
        except Exception as e:
            messagebox.showerror("Erro", f"Data inválida: {e}", parent=self)

# ── NotifOverlay — notificação no canto inferior esquerdo ────────────────────
class NotifOverlay(tk.Toplevel):
    """Popup compacto no canto inferior esquerdo da tela."""
    LARGURA = 290

    def __init__(self, parent, titulo, tarefa_texto, corpo, tipo, ao_fechar, prioridade="Média", fila_total=0):
        super().__init__(parent)
        self._ao_fechar  = ao_fechar
        self._tipo       = tipo
        self.prioridade  = prioridade   # exposto para ordenação externa
        self._tarefa_texto = tarefa_texto  # exposto para deduplicação entre tipos

        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(bg=BORDA)

        cor_prior_map = {"Alta": COR_ALTA, "Média": COR_MEDIA, "Baixa": COR_BAIXA}
        self._cor_barra = cor_prior_map.get(prioridade, ACCENT)
        icone = "⏰" if tipo == "ciclica" else "🔔"
        prior_fg = "#1e1e2e" if prioridade == "Média" else "#fff"

        # Barra superior colorida pela prioridade
        tk.Frame(self, bg=self._cor_barra, height=4).pack(fill="x")

        self._conteudo = tk.Frame(self, bg=BG2, padx=10, pady=7)
        self._conteudo.pack(fill="both", expand=True)

        # Cabeçalho — título já inclui o ícone, não repetir
        cabec = tk.Frame(self._conteudo, bg=BG2); cabec.pack(fill="x")
        tk.Label(cabec, text=titulo, bg=BG2, fg=FG,
                 font=("Segoe UI", 10, "bold")).pack(side="left")
        tk.Button(cabec, text="✕", bg=BG2, fg=FG3, relief="flat", bd=0,
                  font=("Segoe UI", 9), cursor="hand2",
                  activebackground=BG2, activeforeground=ACCENT2,
                  command=self._fechar).pack(side="right")

        # Banner de fila — atualizável
        self._fila_frame = tk.Frame(self._conteudo, bg=ACCENT2, padx=6, pady=2)
        self._lbl_fila   = tk.Label(self._fila_frame, text="", bg=ACCENT2, fg="#fff",
                                    font=("Segoe UI", 8, "bold"))
        self._lbl_fila.pack(anchor="w")

        # Tarefa em destaque
        if tarefa_texto:
            tk.Label(self._conteudo, text=tarefa_texto, bg=BG2,
                     fg="#FFD700", font=("Segoe UI", 12, "bold"),
                     wraplength=self.LARGURA - 20, justify="left").pack(anchor="w", pady=(6, 2))

        # Badge de prioridade
        tk.Label(self._conteudo, text=f"⚑ Prioridade: {prioridade}", bg=self._cor_barra,
                 fg=prior_fg, font=("Segoe UI", 8, "bold"),
                 padx=6, pady=2).pack(anchor="w", pady=(0, 4))

        # Corpo (data agendada)
        if corpo:
            tk.Label(self._conteudo, text=corpo, bg=BG2, fg=FG2,
                     font=("Segoe UI", 9), wraplength=self.LARGURA - 20,
                     justify="left").pack(anchor="w")

        # Botão OK — texto atualizado junto com a fila
        self._btn_ok = tk.Button(self._conteudo, text="OK",
                                 bg=self._cor_barra, fg=prior_fg,
                                 relief="flat", bd=0, font=("Segoe UI", 9, "bold"),
                                 cursor="hand2", activebackground=self._cor_barra,
                                 command=self._fechar)
        self._btn_ok.pack(anchor="e", ipadx=12, ipady=3, pady=(6, 0))

        # Aplica estado inicial da fila
        self.atualizar_fila(fila_total)
        self.update_idletasks()

    # ── API pública ──────────────────────────────────────────────────────────
    def atualizar_fila(self, fila_total: int):
        """Atualiza ao vivo o banner e o botão OK com o tamanho atual da fila."""
        if self._tipo == "agendada" and fila_total > 1:
            atrasadas = fila_total - 1
            self._lbl_fila.config(
                text=f"⚠ {atrasadas} atrasada{'s' if atrasadas != 1 else ''} aguardando na fila")
            self._fila_frame.pack(fill="x", pady=(4, 0))
            ok_txt = f"OK  ({atrasadas} restante{'s' if atrasadas != 1 else ''} →)"
        else:
            self._fila_frame.pack_forget()
            ok_txt = "OK"
        self._btn_ok.config(text=ok_txt)
        self.update_idletasks()

    def posicionar(self, x, y):
        self.update_idletasks()
        h = self.winfo_reqheight()
        self.geometry(f"{self.LARGURA}x{h}+{x}+{y}")

    def get_altura(self):
        self.update_idletasks()
        return self.winfo_reqheight()

    def _fechar(self):
        self._ao_fechar(self._tipo)
        self.destroy()

# ══════════════════════════════════════════════════════════════════════════════
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Lista de Tarefas")
        self.configure(bg=BG)

        # Ajusta o tamanho da janela dinamicamente conforme a resolução da tela
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        w = max(800, min(960, int(sw * 0.65)))
        h = max(520, min(700, int(sh * 0.75)))
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.minsize(750, 480)
        self.resizable(True, True)

        self.tarefas = []
        self.historico = []
        self.cfg = {"notificacoes_ligadas": True, "intervalo_minutos": 30}
        self._prox_notif = 0.0

        # Controle de notificações abertas (máx 1 por tipo)
        self._notif_aberta = {"ciclica": False, "agendada": False}
        self._notif_widgets: dict[str, NotifOverlay] = {}

        # Fila de notificações agendadas pendentes de reconhecimento
        self._fila_agendadas: list[dict] = []  # cada item: {texto, prioridade, notif_agendada}

        self._carregar()
        self._verificar_repeticoes()
        self._build_ui()
        self._render_lista()

        self._prox_notif = time.time() + self.cfg["intervalo_minutos"] * 60
        threading.Thread(target=self._loop_notif, daemon=True).start()
        self._tick()

    # ── Persistência ──────────────────────────────────────────────────────────
    def _carregar(self):
        if not SAVE_FILE.exists():
            return
        try:
            with open(SAVE_FILE, encoding="utf-8") as f:
                d = json.load(f)
            if isinstance(d, list):
                self.tarefas = d
            else:
                self.tarefas   = d.get("tarefas", [])
                self.historico = d.get("historico", [])
                self.cfg = {**self.cfg, **d.get("config", {})}
            for t in self.tarefas:
                t.setdefault("criado_em", agora()); t.setdefault("repeticao", "Sem repetição")
                t.setdefault("prioridade", "Média"); t.setdefault("log", [{"evento": "Criada", "quando": t["criado_em"]}])
                t.setdefault("subtarefas", []); t.setdefault("notif_agendada", ""); t.setdefault("notif_disparada", False)
            self.historico = purgar_hist(self.historico)
        except Exception as e:
            print("Erro ao carregar:", e)

    def _salvar(self):
        with open(SAVE_FILE, "w", encoding="utf-8") as f:
            json.dump({"tarefas": self.tarefas, "historico": self.historico, "config": self.cfg},
                      f, ensure_ascii=False, indent=2)

    def _verificar_repeticoes(self):
        hoje = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        novas = []
        for t in self.tarefas:
            rep = t.get("repeticao", "Sem repetição")
            if rep == "Sem repetição" or not t.get("concluida") or not t.get("concluida_em"):
                continue
            dc = parse_dt(t["concluida_em"])
            if not dc:
                continue
            dc = dc.replace(hour=0, minute=0, second=0, microsecond=0)
            diff = (hoje - dc).days
            if (rep == "Diariamente" and diff >= 1) or (rep == "Semanalmente" and diff >= 7):
                novas.append(nova_tarefa_dict(t["texto"], t.get("prioridade","Média"), t.get("repeticao","Sem repetição")))
        if novas:
            self.tarefas.extend(novas); self._salvar()

    # ── UI ────────────────────────────────────────────────────────────────────
    def _build_ui(self):
        # Header
        hdr = tk.Frame(self, bg="#13131f", height=36)
        hdr.pack(fill="x"); hdr.pack_propagate(False)
        c = tk.Frame(hdr, bg="#13131f"); c.pack(expand=True)
        tk.Label(c, text="📝", bg="#13131f", fg=ACCENT, font=("Segoe UI", 12)).pack(side="left")
        tk.Label(c, text="  Lista de Tarefas", bg="#13131f", fg=FG, font=FNT_HDR).pack(side="left")
        tk.Frame(self, bg=ACCENT, height=2).pack(fill="x")

        # Tabs
        self._tab_bar = tk.Frame(self, bg=BG2, height=32)
        self._tab_bar.pack(fill="x"); self._tab_bar.pack_propagate(False)
        self._tab_btns = {}
        for key, lbl in [("tarefas","  Tarefas Pendentes"),("pesquisa","  🔍 Pesquisar"),
                          ("historico","  📋 Histórico"),("opcoes","  ⚙ Opções")]:
            btn = tk.Button(self._tab_bar, text=lbl, relief="flat", bd=0,
                            bg=BG2, fg=FG2, activebackground=BG3, activeforeground=FG,
                            font=FNT_BODY_B, cursor="hand2", padx=12,
                            command=lambda k=key: self._mudar_aba(k))
            btn.pack(side="left", fill="y")
            self._tab_btns[key] = btn
        tk.Frame(self, bg=BORDA, height=1).pack(fill="x")

        # Painéis
        self._paineis = {}
        self._container = tk.Frame(self, bg=BG)
        self._container.pack(fill="both", expand=True)

        self._painel_tarefas()
        self._painel_pesquisa()
        self._painel_historico()
        self._painel_opcoes()
        self._mudar_aba("tarefas")

    def _mudar_aba(self, key):
        for k, btn in self._tab_btns.items():
            if k == key:
                btn.config(bg=ACCENT, fg="#fff", activebackground=ACCENT_H, activeforeground="#fff")
            else:
                btn.config(bg=BG2, fg=FG2, activebackground=BG3, activeforeground=FG)
        for f in self._paineis.values():
            f.place_forget()
        self._paineis[key].place(relx=0, rely=0, relwidth=1, relheight=1)
        if key == "historico": self._render_historico()
        elif key == "pesquisa": self._inp_pesquisa.focus(); self._pesquisar()

    def _reg_painel(self, key):
        f = tk.Frame(self._container, bg=BG)
        self._paineis[key] = f
        return f

    # ── Painel Tarefas ─────────────────────────────────────────────────────────
    def _painel_tarefas(self):
        f = self._reg_painel("tarefas")

        bloco = tk.Frame(f, bg=BG2, highlightbackground=BORDA, highlightthickness=1)
        bloco.pack(fill="x", padx=8, pady=(6, 4))
        tk.Frame(bloco, bg=ACCENT, height=2).pack(fill="x")

        # Linha entrada principal
        r1 = tk.Frame(bloco, bg=BG2)
        r1.pack(fill="x", padx=8, pady=(6, 2))
        self._inp_tarefa = tk.Entry(r1, bg=BG3, fg=FG, insertbackground=FG, relief="flat",
                                    font=("Segoe UI", 10), highlightthickness=1,
                                    highlightbackground=BORDA2, highlightcolor=ACCENT, bd=0)
        self._inp_tarefa.pack(side="left", fill="x", expand=True, ipady=5)
        self._inp_tarefa.bind("<Return>", lambda e: self._adicionar_tarefa())
        tk.Frame(r1, bg=BG2, width=6).pack(side="left")
        tk.Button(r1, text="＋  Adicionar", bg=ACCENT, fg="#fff", relief="flat", bd=0,
                  font=FNT_BODY_B, cursor="hand2", activebackground=ACCENT_H, activeforeground="#fff",
                  command=self._adicionar_tarefa).pack(side="left", ipady=5, ipadx=10)

        # Notificação agendada — entrada rápida
        r_dt = tk.Frame(bloco, bg=BG2)
        r_dt.pack(fill="x", padx=8, pady=(0, 4))
        tk.Label(r_dt, text="🔔 Notif.:", bg=BG2, fg=FG2, font=FNT_SMALL).pack(side="left")

        self._inp_agendada = tk.Entry(r_dt, bg=BG3, fg=FG, insertbackground=FG, relief="flat",
                                      font=("Consolas", 9), width=16, highlightthickness=1,
                                      highlightbackground=BORDA, highlightcolor=ACCENT, bd=0)
        self._inp_agendada.pack(side="left", ipady=3, padx=(4, 3))

        # Botão para abrir o picker de data
        tk.Button(r_dt, text="📅", bg=BG3, fg=FG2, relief="flat", bd=0,
                  font=FNT_SMALL, cursor="hand2", activebackground=BORDA, activeforeground=FG,
                  command=self._abrir_picker).pack(side="left", ipadx=5, ipady=3, padx=(0, 3))

        # Botões rápidos: +15 Min, +30 min, +1h, amanhã
        for label, delta in [
            ("+15m", timedelta(minutes=15)),
            ("+30m", timedelta(minutes=30)),
            ("+1h", timedelta(hours=1)),
            ("Amanhã", None)
        ]:
            tk.Button(
                r_dt,
                text=label,
                bg=BG3,
                fg=FG3,
                relief="flat",
                bd=0,
                font=("Segoe UI", 8),
                cursor="hand2",
                activebackground=BORDA,
                activeforeground=FG,
                command=lambda l=label, d=delta: self._data_rapida(l, d)
            ).pack(side="left", ipadx=4, ipady=2, padx=1)

        tk.Button(r_dt, text="✕", bg=BG2, fg=FG3, relief="flat", bd=0, cursor="hand2",
                  font=("Segoe UI", 9), activebackground=BG2, activeforeground=ACCENT2,
                  command=lambda: self._inp_agendada.delete(0, "end")).pack(side="left", padx=3)

        sep_line(bloco, BORDA)

        # Repetição + Prioridade
        opts = tk.Frame(bloco, bg=BG2)
        opts.pack(fill="x", padx=8, pady=4)

        tk.Label(opts, text="Repetir:", bg=BG2, fg=FG2, font=FNT_SMALL_B).pack(side="left")
        self._rep_var = tk.StringVar(value="Sem repetição")
        self._rep_btns = {}

        def _sel_rep(val):
            self._rep_var.set(val)
            for v, (btn, cor) in self._rep_btns.items():
                if v == val:
                    btn.config(bg=cor, fg="#fff", font=("Segoe UI", 10, "bold"))
                else:
                    btn.config(bg=BG3, fg=cor, font=FNT_SMALL)

        for val, cor in [("Sem repetição", FG2), ("Diariamente", COR_DIARIO), ("Semanalmente", COR_SEMANAL)]:
            btn = tk.Button(opts, text=val, bg=BG3, fg=cor,
                            relief="flat", bd=0, cursor="hand2", font=FNT_SMALL,
                            activebackground=cor, activeforeground="#fff",
                            padx=10, pady=4,
                            command=lambda v=val: _sel_rep(v))
            btn.pack(side="left", padx=(4,0))
            self._rep_btns[val] = (btn, cor)

        _sel_rep("Sem repetição")

        tk.Frame(opts, bg=BORDA, width=1).pack(side="left", fill="y", padx=10)
        tk.Label(opts, text="Prioridade:", bg=BG2, fg=FG2, font=FNT_SMALL_B).pack(side="left")
        self._pri_var = tk.StringVar(value="Média")
        self._pri_btns = {}

        def _sel_pri(val):
            self._pri_var.set(val)
            for v, (btn, cor) in self._pri_btns.items():
                if v == val:
                    btn.config(bg=cor, fg="#fff" if cor != COR_MEDIA else "#1e1e2e",
                               relief="sunken", font=("Segoe UI", 10, "bold"))
                else:
                    btn.config(bg=BG3, fg=cor, relief="flat", font=FNT_SMALL)

        for val, cor, icone in [("Alta", COR_ALTA, ""), ("Média", COR_MEDIA, ""), ("Baixa", COR_BAIXA, "")]:
            btn = tk.Button(opts, text=val, bg=BG3, fg=cor,
                            relief="flat", bd=0, cursor="hand2", font=FNT_SMALL,
                            activebackground=cor, activeforeground="#fff",
                            padx=12, pady=4,
                            command=lambda v=val: _sel_pri(v))
            btn.pack(side="left", padx=(4, 0))
            self._pri_btns[val] = (btn, cor)

        _sel_pri("Média")

        # Status bar
        sb = tk.Frame(f, bg=BG)
        sb.pack(fill="x", padx=8, pady=(0, 2))
        self._lbl_status = tk.Label(sb, text="", bg=BG, fg=FG2, font=FNT_MONO, anchor="w")
        self._lbl_status.pack(side="left")
        self._lbl_countdown = tk.Label(sb, text="", bg=BG, fg=FG3, font=FNT_MONO, anchor="e")
        self._lbl_countdown.pack(side="right")
        sep_line(f, BORDA)

        self._scroll_lista = ScrollFrame(f, bg=BG)
        self._scroll_lista.pack(fill="both", expand=True)

        sep_line(f, BORDA)
        rodape = tk.Frame(f, bg=BG2, height=30); rodape.pack(fill="x"); rodape.pack_propagate(False)
        tk.Button(rodape, text="🧹  Limpar concluídas", bg=BG2, fg=FG2, relief="flat", bd=0,
                  font=FNT_SMALL, cursor="hand2", activebackground=BG3, activeforeground=FG,
                  command=self._limpar_concluidas).pack(side="left", padx=8, pady=5)

    def _abrir_picker(self):
        """Abre o DateTimePicker e preenche o campo de data ao confirmar."""
        valor_atual = self._inp_agendada.get().strip()
        ini = parse_dt(valor_atual) if valor_atual else None

        def _cb(dt_str):
            self._inp_agendada.delete(0, "end")
            self._inp_agendada.insert(0, dt_str)

        DateTimePicker(self, _cb, ini)

    def _data_rapida(self, label, delta):
        base = datetime.now()

        if label == "Amanhã":
            dt = base + timedelta(days=1)
        else:
            dt = base + delta

        self._inp_agendada.delete(0, "end")
        self._inp_agendada.insert(0, dt.strftime("%d/%m/%Y %H:%M"))

    # ── Painel Pesquisa ────────────────────────────────────────────────────────
    def _painel_pesquisa(self):
        f = self._reg_painel("pesquisa")
        bloco = tk.Frame(f, bg=BG2, highlightbackground=BORDA, highlightthickness=1)
        bloco.pack(fill="x", padx=8, pady=(8, 4))
        tk.Frame(bloco, bg=ACCENT, height=2).pack(fill="x")
        row = tk.Frame(bloco, bg=BG2); row.pack(fill="x", padx=8, pady=6)
        tk.Label(row, text="🔍", bg=BG2, fg=ACCENT, font=FNT_ICON).pack(side="left")
        self._inp_pesquisa = tk.Entry(row, bg=BG3, fg=FG, insertbackground=FG, relief="flat",
                                      font=("Segoe UI", 10), highlightthickness=1,
                                      highlightbackground=BORDA2, highlightcolor=ACCENT, bd=0)
        self._inp_pesquisa.pack(side="left", fill="x", expand=True, ipady=5, padx=(6,6))
        self._inp_pesquisa.bind("<KeyRelease>", lambda e: self._pesquisar())
        tk.Button(row, text="Pesquisar", bg=ACCENT, fg="#fff", relief="flat", bd=0,
                  font=FNT_BODY_B, cursor="hand2", activebackground=ACCENT_H,
                  command=self._pesquisar).pack(side="left", ipady=5, ipadx=10)
        self._lbl_pesq = tk.Label(f, text="Digite para pesquisar…", bg=BG, fg=FG2, font=FNT_SMALL, anchor="w")
        self._lbl_pesq.pack(fill="x", padx=16, pady=(0, 4))
        sep_line(f, BORDA)
        self._scroll_pesq = ScrollFrame(f, bg=BG)
        self._scroll_pesq.pack(fill="both", expand=True)

    # ── Painel Histórico ───────────────────────────────────────────────────────
    def _painel_historico(self):
        f = self._reg_painel("historico")
        bloco = tk.Frame(f, bg=BG2, highlightbackground=BORDA, highlightthickness=1)
        bloco.pack(fill="x", padx=8, pady=(8, 4))
        tk.Frame(bloco, bg=COR_SEMANAL, height=2).pack(fill="x")
        row = tk.Frame(bloco, bg=BG2); row.pack(fill="x", padx=8, pady=6)
        tk.Label(row, text="📋  Histórico de Tarefas", bg=BG2, fg=FG, font=FNT_TITLE).pack(side="left")
        tk.Label(row, text=f"(últimos {DIAS_HIST} dias)", bg=BG2, fg=FG2, font=FNT_SMALL).pack(side="left", padx=6)
        self._lbl_hist_info = tk.Label(f, text="", bg=BG, fg=FG2, font=FNT_SMALL, anchor="w")
        self._lbl_hist_info.pack(fill="x", padx=16, pady=(0, 4))
        sep_line(f, BORDA)
        self._scroll_hist = ScrollFrame(f, bg=BG)
        self._scroll_hist.pack(fill="both", expand=True)

    # ── Painel Opções ──────────────────────────────────────────────────────────
    def _painel_opcoes(self):
        f = self._reg_painel("opcoes")
        outer = tk.Frame(f, bg=BG); outer.pack(fill="both", expand=True, padx=8, pady=8)

        def secao(titulo, cor=ACCENT):
            bloco = tk.Frame(outer, bg=BG2, highlightbackground=BORDA, highlightthickness=1)
            bloco.pack(fill="x", pady=(0,10))
            tk.Frame(bloco, bg=cor, height=3).pack(fill="x")
            tk.Label(bloco, text=titulo.upper(), bg=BG2, fg=FG3, font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=14, pady=(8,4))
            inner = tk.Frame(bloco, bg=BG2); inner.pack(fill="x", padx=14, pady=(0,12))
            return inner

        s1 = secao("🔔  Notificação Cíclica")
        row = tk.Frame(s1, bg=BG2); row.pack(fill="x")
        tk.Label(row, text="Status:", bg=BG2, fg=FG2, font=FNT_SMALL).pack(side="left")
        self._btn_toggle = tk.Button(row, text="● Ligadas", bg=FG_OK, fg="#fff", relief="flat", bd=0,
                                      font=FNT_SMALL_B, cursor="hand2", activebackground=FG_OK2,
                                      activeforeground="#fff", command=self._toggle_notif)
        self._btn_toggle.pack(side="left", padx=8, ipadx=12, ipady=5)
        tk.Label(row, text="Intervalo:", bg=BG2, fg=FG2, font=FNT_SMALL).pack(side="left", padx=(8,0))
        self._inp_intervalo = tk.Spinbox(row, from_=1, to=999, width=5, bg=BG3, fg=FG,
                                          font=("Segoe UI", 11), relief="flat", buttonbackground=BG3,
                                          highlightthickness=1, highlightbackground=BORDA)
        self._inp_intervalo.delete(0,"end"); self._inp_intervalo.insert(0, str(self.cfg["intervalo_minutos"]))
        self._inp_intervalo.pack(side="left", padx=6, ipady=4)
        tk.Label(row, text="min", bg=BG2, fg=FG2, font=FNT_SMALL).pack(side="left")
        tk.Button(row, text="Aplicar", bg=ACCENT, fg="#fff", relief="flat", bd=0,
                  font=FNT_SMALL_B, cursor="hand2", activebackground=ACCENT_H,
                  command=self._aplicar_intervalo).pack(side="left", padx=8, ipadx=12, ipady=5)
        self._lbl_cd_opc = tk.Label(row, text="", bg=BG2, fg=FG3, font=FNT_MONO)
        self._lbl_cd_opc.pack(side="left")
        if NOTIF_BACKEND is None:
            tk.Label(s1, text="⚠  winotify/win10toast não instalado — usando popups internos",
                     bg=BG2, fg=FG_WARN, font=FNT_SMALL).pack(anchor="w", pady=(4,0))

        s2 = secao("💾  Importar / Exportar")
        row2 = tk.Frame(s2, bg=BG2); row2.pack(anchor="w")
        tk.Button(row2, text="⬇  Exportar JSON", bg=BG3, fg=FG2, relief="flat", bd=0,
                  font=FNT_BODY_B, cursor="hand2", activebackground=BORDA, activeforeground=FG,
                  command=self._exportar).pack(side="left", ipadx=14, ipady=7, padx=(0,8))
        tk.Button(row2, text="⬆  Importar JSON", bg=BG3, fg=FG2, relief="flat", bd=0,
                  font=FNT_BODY_B, cursor="hand2", activebackground=BORDA, activeforeground=FG,
                  command=self._importar).pack(side="left", ipadx=14, ipady=7)

        s3 = secao("⚠  Zona de Perigo", cor=ACCENT2)
        tk.Label(s3, text="Remove TODAS as tarefas e o histórico permanentemente.",
                 bg=BG2, fg=FG2, font=FNT_SMALL).pack(anchor="w", pady=(0,6))
        tk.Button(s3, text="🗑  Excluir todas as tarefas", bg=ACCENT2, fg="#fff", relief="flat", bd=0,
                  font=FNT_BODY_B, cursor="hand2", activebackground=ACCENT2_H,
                  command=self._excluir_tudo).pack(fill="x", ipady=9)

    # ══════════════════════════════════════════════════════════════════════════
    # RENDER LISTA
    # ══════════════════════════════════════════════════════════════════════════
    def _render_lista(self):
        self._scroll_lista.clear()
        p = [t for t in self.tarefas if not t.get("concluida")]
        self._lbl_status.config(text=f"  {len(p)} pendente(s)  ·  {len(self.tarefas)} no total")
        if not self.tarefas:
            tk.Label(self._scroll_lista.inner, text="Nenhuma tarefa ainda. Adicione uma acima!",
                     bg=BG, fg=FG2, font=FNT_BODY).pack(pady=40)
            return
        sorted_t = sorted(self.tarefas, key=lambda t: (
            1 if t.get("concluida") else 0,
            PRIOR_ORD.get(t.get("prioridade","Média"),1), t.get("criado_em","")))
        for t in sorted_t:
            self._card_tarefa(self._scroll_lista.inner, self.tarefas.index(t), t)

    def _card_tarefa(self, parent, idx, t):
        conc  = t.get("concluida", False)
        prior = t.get("prioridade","Média")
        rep   = t.get("repeticao","Sem repetição")
        cp    = cor_prior(prior)
        cr    = cor_rep(rep)
        bg_c  = BG2 if conc else BG3

        outer = tk.Frame(parent, bg=bg_c, highlightbackground=BORDA if conc else cp, highlightthickness=1)
        outer.pack(fill="x", padx=8, pady=(0,3))
        tk.Frame(outer, bg=BORDA if conc else cp, width=4).pack(side="left", fill="y")

        body = tk.Frame(outer, bg=bg_c); body.pack(side="left", fill="both", expand=True)

        # Linha principal
        r1 = tk.Frame(body, bg=bg_c); r1.pack(fill="x", padx=(6,6), pady=(4,1))
        chk_c = FG_OK if conc else ACCENT
        tk.Button(r1, text="☑" if conc else "☐", bg=bg_c, fg=chk_c, relief="flat", bd=0,
                  font=("Segoe UI", 12), cursor="hand2", activebackground=bg_c, activeforeground=FG_OK,
                  command=lambda i=idx: self._toggle_tarefa(i)).pack(side="left")
        tf = ("Segoe UI", 10, "overstrike") if conc else ("Segoe UI", 10)
        tk.Label(r1, text=t["texto"], bg=bg_c, fg=FG2 if conc else FG, font=tf,
                 anchor="w", justify="left", wraplength=520).pack(side="left", fill="x", expand=True, padx=5)
        bdg = tk.Frame(r1, bg=bg_c); bdg.pack(side="right")
        if not conc:
            _badge(bdg, prior, cp, "#fff" if prior != "Média" else "#1e1e2e")
        if cr:
            _badge(bdg, "🔁 "+rep, cr, "#fff")
        if t.get("notif_agendada") and not conc:
            dt = parse_dt(t["notif_agendada"])
            if dt:
                _badge(bdg, "🔔 "+dt.strftime("%d/%m %H:%M"), "#1a4a3a", "#7ef0d8")
        if conc:
            _badge(bdg, "✅ Concluída", FG_OK, "#1e1e2e")
        tk.Button(r1, text="✕", bg=bg_c, fg=ACCENT2, relief="flat", bd=0,
                  font=("Segoe UI", 9), cursor="hand2", activebackground=bg_c, activeforeground="#ff6b6b",
                  command=lambda i=idx: self._remover_tarefa(i)).pack(side="right", padx=(3,0))

        # Controles inline
        r2 = tk.Frame(body, bg=bg_c); r2.pack(fill="x", padx=(24,6), pady=(0,1))
        tk.Label(r2, text="🔁", bg=bg_c, fg=FG3, font=("Segoe UI",9)).pack(side="left")
        _card_rep_btns = {}

        def _sel_card_rep(val, i=idx):
            self._set_repeticao(i, val)
            for v, btn in _card_rep_btns.items():
                cor_v = {"Sem repetição": FG2, "Diariamente": COR_DIARIO, "Semanalmente": COR_SEMANAL}[v]
                if v == val:
                    btn.config(bg=cor_v, fg="#fff", font=("Segoe UI", 10, "bold"))
                else:
                    btn.config(bg=bg_c, fg=cor_v, font=FNT_SMALL)

        for rv, cor in [("Sem repetição", FG2), ("Diariamente", COR_DIARIO), ("Semanalmente", COR_SEMANAL)]:
            is_sel = (rv == rep)
            btn = tk.Button(r2, text=rv,
                            bg=cor if is_sel else bg_c,
                            fg="#fff" if is_sel else cor,
                            relief="flat", bd=0, cursor="hand2",
                            font=("Segoe UI", 10, "bold") if is_sel else FNT_SMALL,
                            activebackground=cor, activeforeground="#fff",
                            padx=8, pady=2,
                            command=lambda v=rv: _sel_card_rep(v))
            btn.pack(side="left", padx=2)
            _card_rep_btns[rv] = btn
        tk.Frame(r2, bg=BORDA, width=1).pack(side="left", fill="y", padx=8)
        tk.Label(r2, text="⚑", bg=bg_c, fg=FG3, font=("Segoe UI",9)).pack(side="left")
        _card_pri_btns = {}

        def _sel_card_pri(val, i=idx):
            self._set_prioridade(i, val)
            for v, btn in _card_pri_btns.items():
                cor_v = {"Alta": COR_ALTA, "Média": COR_MEDIA, "Baixa": COR_BAIXA}[v]
                if v == val:
                    btn.config(bg=cor_v, fg="#fff" if cor_v != COR_MEDIA else "#1e1e2e",
                               font=("Segoe UI", 10, "bold"))
                else:
                    btn.config(bg=bg_c, fg=cor_v, font=FNT_SMALL)

        for pv, cor, ico in [("Alta", COR_ALTA, ""), ("Média", COR_MEDIA, ""), ("Baixa", COR_BAIXA, "")]:
            is_sel = (pv == prior)
            btn = tk.Button(r2, text=pv,
                            bg=cor if is_sel else bg_c,
                            fg=("#fff" if cor != COR_MEDIA else "#1e1e2e") if is_sel else cor,
                            relief="flat", bd=0, cursor="hand2",
                            font=("Segoe UI", 10, "bold") if is_sel else FNT_SMALL,
                            activebackground=cor, activeforeground="#fff",
                            padx=8, pady=2,
                            command=lambda v=pv: _sel_card_pri(v))
            btn.pack(side="left", padx=2)
            _card_pri_btns[pv] = btn

        # Linha de reagendamento de notificação (apenas tarefas não concluídas)
        if not conc:
            r3 = tk.Frame(body, bg=bg_c); r3.pack(fill="x", padx=(24,6), pady=(1,3))
            tk.Label(r3, text="🔔", bg=bg_c, fg=FG3, font=("Segoe UI",9)).pack(side="left")

            notif_var = tk.StringVar(value=t.get("notif_agendada",""))
            inp_notif = tk.Entry(r3, textvariable=notif_var, bg=BG3, fg=FG,
                                 insertbackground=FG, relief="flat", font=("Consolas", 9),
                                 width=16, highlightthickness=1,
                                 highlightbackground=BORDA, highlightcolor=ACCENT, bd=0)
            inp_notif.pack(side="left", ipady=3, padx=(4,4))

            def _abrir_picker_card(i=idx, var=notif_var, inp=inp_notif):
                val_atual = var.get().strip()
                ini = parse_dt(val_atual) if val_atual else None
                def _cb(dt_str, i_=i, v_=var, inp_=inp):
                    v_.set(dt_str)
                    self._reagendar_notif(i_, dt_str)
                DateTimePicker(self, _cb, ini)

            def _data_rapida_card(label, delta, i=idx, var=notif_var):
                base = datetime.now()
                if label == "Amanhã":
                    dt = (base + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
                else:
                    dt = base + delta
                s = dt.strftime("%d/%m/%Y %H:%M")
                var.set(s)
                self._reagendar_notif(i, s)

            def _limpar_notif_card(i=idx, var=notif_var):
                var.set("")
                self._reagendar_notif(i, "")

            tk.Button(r3, text="📅", bg=bg_c, fg=FG2, relief="flat", bd=0,
                      font=("Segoe UI",9), cursor="hand2", activebackground=BORDA,
                      command=_abrir_picker_card).pack(side="left", padx=(0,2))

            for label, delta in [("+1h", timedelta(hours=1)), ("+2h", timedelta(hours=2)),
                                  ("Amanhã", None), ("+1sem", timedelta(weeks=1))]:
                tk.Button(r3, text=label, bg=BG3, fg=FG3, relief="flat", bd=0,
                          font=("Segoe UI", 8), cursor="hand2", activebackground=BORDA,
                          command=lambda l=label, d=delta: _data_rapida_card(l, d)
                          ).pack(side="left", ipadx=4, ipady=2, padx=1)

            tk.Button(r3, text="✕", bg=bg_c, fg=FG3, relief="flat", bd=0,
                      font=("Segoe UI",9), cursor="hand2",
                      activebackground=bg_c, activeforeground=ACCENT2,
                      command=_limpar_notif_card).pack(side="left", padx=(2,0))

        self._widget_subtarefas(body, idx, t, bg_c)
        if conc and t.get("concluida_em"):
            tk.Label(body, text=f"  ✅ Concluída em {t['concluida_em']}", bg=bg_c, fg=FG_OK, font=FNT_MONO).pack(anchor="w", padx=(36,8), pady=(0,6))

    def _widget_subtarefas(self, parent, idx, t, bg_c):
        subs = t.get("subtarefas", [])
        wrap = tk.Frame(parent, bg=bg_c); wrap.pack(fill="x", padx=(36,8), pady=(2,0))
        aberto = tk.BooleanVar(value=False)
        lbl_txt = tk.StringVar()
        lista_f = tk.Frame(wrap, bg=bg_c)

        def atualizar_lbl():
            n = len(t.get("subtarefas", [])); done = sum(1 for s in t.get("subtarefas",[]) if s.get("concluida"))
            lbl_txt.set(("▼ " if aberto.get() else "▶ ") + f"Subtarefas ({done}/{n})")

        def toggle():
            aberto.set(not aberto.get())
            if aberto.get(): lista_f.pack(fill="x", pady=(2,0))
            else: lista_f.pack_forget()
            atualizar_lbl()

        atualizar_lbl()
        tk.Button(wrap, textvariable=lbl_txt, bg=bg_c, fg=FG2, relief="flat", bd=0,
                  font=FNT_SMALL, cursor="hand2", anchor="w",
                  activebackground=bg_c, activeforeground=FG, command=toggle).pack(anchor="w")

        def render_subs():
            for w in lista_f.winfo_children(): w.destroy()
            atualizar_lbl()
            for si, st in enumerate(t.get("subtarefas",[])):
                row = tk.Frame(lista_f, bg=bg_c); row.pack(fill="x", pady=1)
                chk = "☑" if st.get("concluida") else "☐"
                tk.Button(row, text=chk, bg=bg_c, fg=FG_OK if st.get("concluida") else FG2,
                          relief="flat", bd=0, font=("Segoe UI",13), cursor="hand2",
                          activebackground=bg_c, command=lambda si_=si: _tog_sub(si_)).pack(side="left")
                stf = ("Segoe UI",10,"overstrike") if st.get("concluida") else ("Segoe UI",10)
                tk.Label(row, text=st["texto"], bg=bg_c, fg=FG2 if st.get("concluida") else FG,
                         font=stf, anchor="w").pack(side="left", fill="x", expand=True, padx=4)
                if st.get("concluida_em"):
                    tk.Label(row, text=st["concluida_em"], bg=bg_c, fg=FG3, font=FNT_MONO).pack(side="left", padx=4)
                tk.Button(row, text="✕", bg=bg_c, fg=ACCENT2, relief="flat", bd=0,
                          font=("Segoe UI",9), cursor="hand2", activebackground=bg_c, activeforeground="#ff6b6b",
                          command=lambda si_=si: _del_sub(si_)).pack(side="right", padx=2)
            add_row = tk.Frame(lista_f, bg=bg_c); add_row.pack(fill="x", pady=(4,6))
            add_inp = tk.Entry(add_row, bg=BG3, fg=FG, insertbackground=FG, relief="flat",
                               font=("Segoe UI",10), highlightthickness=1, highlightbackground=BORDA, bd=0)
            add_inp.pack(side="left", fill="x", expand=True, ipady=5)
            add_inp.insert(0,"Nova subtarefa…")
            add_inp.bind("<FocusIn>", lambda e: add_inp.delete(0,"end") if add_inp.get()=="Nova subtarefa…" else None)
            def _add():
                v = add_inp.get().strip()
                if not v or v=="Nova subtarefa…": return
                a = agora()
                t["subtarefas"].append({"texto":v,"concluida":False,"criado_em":a,"concluida_em":None,
                                         "log":[{"evento":"Sub criada","quando":a,"subtarefa":v}]})
                self._salvar(); render_subs()
            add_inp.bind("<Return>", lambda e: _add())
            tk.Button(add_row, text="＋ Add", bg=ACCENT, fg="#fff", relief="flat", bd=0,
                      font=("Segoe UI",9,"bold"), cursor="hand2", activebackground=ACCENT_H,
                      command=_add).pack(side="left", padx=(6,0), ipadx=10, ipady=5)

        def _tog_sub(si):
            st=t["subtarefas"][si]; a=agora()
            st["concluida"]=not st["concluida"]
            if st["concluida"]: st["concluida_em"]=a; st.setdefault("log",[]).append({"evento":"Sub concluída","quando":a,"subtarefa":st["texto"]})
            else: st["concluida_em"]=None; st.setdefault("log",[]).append({"evento":"Sub reaberta","quando":a,"subtarefa":st["texto"]})
            self._salvar(); render_subs()

        def _del_sub(si):
            st=t["subtarefas"][si]; a=agora()
            t.setdefault("log",[]).append({"evento":"Sub removida","quando":a,"subtarefa":st["texto"]})
            t["subtarefas"].pop(si); self._salvar(); render_subs()

        render_subs()

    # ══════════════════════════════════════════════════════════════════════════
    # RENDER HISTÓRICO
    # ══════════════════════════════════════════════════════════════════════════
    def _render_historico(self):
        self._scroll_hist.clear()
        sorted_h = sorted(self.historico,
            key=lambda h: parse_dt(h.get("concluida_em") or h.get("criado_em","")) or datetime.min, reverse=True)
        self._lbl_hist_info.config(text=f"  {len(sorted_h)} tarefa(s) · histórico dos últimos {DIAS_HIST} dias")
        if not sorted_h:
            tk.Label(self._scroll_hist.inner, text="Nenhuma tarefa nos últimos 30 dias.", bg=BG, fg=FG2, font=FNT_BODY).pack(pady=40)
            return
        for item in sorted_h:
            self._card_hist(self._scroll_hist.inner, item)

    def _card_hist(self, parent, item):
        prior = item.get("prioridade","Média"); rep = item.get("repeticao","Sem repetição")
        cp = cor_prior(prior); cr = cor_rep(rep); conc = bool(item.get("concluida_em"))
        subs = item.get("subtarefas",[]); log = [e for e in item.get("log",[]) if not e.get("subtarefa")]

        outer = tk.Frame(parent, bg=BG2, highlightbackground=cp if conc else BORDA, highlightthickness=1)
        outer.pack(fill="x", padx=12, pady=(0,8))
        tk.Frame(outer, bg=cp, width=5).pack(side="left", fill="y")
        body = tk.Frame(outer, bg=BG2); body.pack(side="left", fill="both", expand=True)

        head = tk.Frame(body, bg=BG2); head.pack(fill="x", padx=10, pady=(10,4))
        esq = tk.Frame(head, bg=BG2); esq.pack(side="left", fill="x", expand=True)
        tk.Label(esq, text=item["texto"], bg=BG2, fg=FG, font=FNT_TITLE, anchor="w", justify="left", wraplength=560).pack(anchor="w")
        bdg_row = tk.Frame(esq, bg=BG2); bdg_row.pack(anchor="w", pady=(3,0))
        _badge(bdg_row, f"⚑ {prior}", cp, "#fff" if prior!="Média" else "#1e1e2e")
        if cr: _badge(bdg_row, f"🔁 {rep}", cr, "#fff")
        if conc: _badge(bdg_row, "✅ Concluída", FG_OK, "#1e1e2e")
        else: _badge(bdg_row, "⏳ Pendente", ACCENT2, "#fff")
        if item.get("notif_agendada"):
            dt = parse_dt(item["notif_agendada"])
            if dt: _badge(bdg_row, "🔔 "+dt.strftime("%d/%m/%Y %H:%M"), "#1a4a3a", "#7ef0d8")
        if conc:
            tk.Button(head, text="↩  Reabrir", bg=BG, fg=ACCENT, relief="flat", bd=1,
                      font=FNT_SMALL_B, cursor="hand2", highlightbackground=BORDA, highlightthickness=1,
                      activebackground=BG3, activeforeground=ACCENT,
                      command=lambda i=item: self._reabrir(i)).pack(side="right", ipadx=10, ipady=5)

        drow = tk.Frame(body, bg=BG2); drow.pack(fill="x", padx=10, pady=(0,4))
        if item.get("criado_em"): tk.Label(drow, text=f"🕐 Criada: {item['criado_em']}", bg=BG2, fg=FG3, font=FNT_MONO).pack(side="left", padx=(0,14))
        if item.get("concluida_em"): tk.Label(drow, text=f"✅ Concluída: {item['concluida_em']}", bg=BG2, fg=FG_OK, font=FNT_MONO).pack(side="left")

        sep_line(body, BORDA, pady=2)

        if log:
            tk.Label(body, text="HISTÓRICO DE EVENTOS", bg=BG2, fg=FG3, font=("Segoe UI",8,"bold")).pack(anchor="w", padx=10, pady=(4,2))
            for e in log:
                ico, cor = icone_log(e.get("evento",""))
                row = tk.Frame(body, bg=BG2); row.pack(fill="x", padx=10, pady=1)
                tk.Label(row, text=ico, bg=BG2, fg=cor, font=("Segoe UI",10), width=3).pack(side="left")
                tk.Label(row, text=e.get("evento",""), bg=BG2, fg=cor, font=FNT_SMALL_B, width=12, anchor="w").pack(side="left")
                tk.Label(row, text=e.get("quando",""), bg=BG2, fg=FG3, font=FNT_MONO).pack(side="left", padx=6)

        if subs:
            sep_line(body, BORDA, pady=2)
            done_s = sum(1 for s in subs if s.get("concluida"))
            tk.Label(body, text=f"SUBTAREFAS ({done_s}/{len(subs)} concluídas)", bg=BG2, fg=FG3,
                     font=("Segoe UI",8,"bold")).pack(anchor="w", padx=10, pady=(4,2))
            for st in subs:
                st_f = tk.Frame(body, bg=BG3, highlightbackground=BORDA, highlightthickness=1)
                st_f.pack(fill="x", padx=10, pady=(0,4))
                tk.Frame(st_f, bg=FG_OK if st.get("concluida") else BORDA, width=3).pack(side="left", fill="y")
                st_b = tk.Frame(st_f, bg=BG3); st_b.pack(side="left", fill="both", expand=True, padx=8, pady=6)
                st_r = tk.Frame(st_b, bg=BG3); st_r.pack(fill="x")
                tk.Label(st_r, text="☑" if st.get("concluida") else "☐", bg=BG3,
                         fg=FG_OK if st.get("concluida") else FG2, font=("Segoe UI",13)).pack(side="left")
                stf = ("Segoe UI",10,"overstrike") if st.get("concluida") else ("Segoe UI",10)
                tk.Label(st_r, text=st["texto"], bg=BG3, fg=FG2 if st.get("concluida") else FG,
                         font=stf, anchor="w", wraplength=540).pack(side="left", padx=6)
        tk.Frame(body, bg=BG2, height=4).pack()

    # ══════════════════════════════════════════════════════════════════════════
    # RENDER PESQUISA
    # ══════════════════════════════════════════════════════════════════════════
    def _pesquisar(self):
        self._scroll_pesq.clear()
        termo = self._inp_pesquisa.get().strip().lower()
        if not termo:
            self._lbl_pesq.config(text="Digite para pesquisar…"); return

        pool = {}
        for t in self.tarefas:
            k = t["texto"]+"|"+t.get("criado_em","")
            if k not in pool: pool[k] = t
        for h in self.historico:
            k = h["texto"]+"|"+h.get("criado_em","")
            if k not in pool: pool[k] = h

        res = [v for v in pool.values()
               if termo in v["texto"].lower() or any(termo in s["texto"].lower() for s in v.get("subtarefas",[]))]
        res.sort(key=lambda v: parse_dt((v.get("log") or [{}])[-1].get("quando") or v.get("criado_em","")) or datetime.min, reverse=True)

        self._lbl_pesq.config(text=f'  {len(res)} resultado(s) para "{self._inp_pesquisa.get().strip()}"')
        if not res:
            tk.Label(self._scroll_pesq.inner, text="Nenhuma tarefa encontrada.", bg=BG, fg=FG2, font=FNT_BODY).pack(pady=40)
            return
        for item in res:
            self._card_pesq(self._scroll_pesq.inner, item, termo)

    def _card_pesq(self, parent, item, termo):
        prior = item.get("prioridade","Média"); rep = item.get("repeticao","Sem repetição")
        cp = cor_prior(prior); cr = cor_rep(rep)
        conc = item.get("concluida",False) or bool(item.get("concluida_em"))
        txt = item["texto"]; idx_t = txt.lower().find(termo)

        outer = tk.Frame(parent, bg=BG2, highlightbackground=cp if not conc else BORDA, highlightthickness=1)
        outer.pack(fill="x", padx=12, pady=(0,8))
        tk.Frame(outer, bg=cp, width=5).pack(side="left", fill="y")
        body = tk.Frame(outer, bg=BG2); body.pack(side="left", fill="both", expand=True)

        head = tk.Frame(body, bg=BG2); head.pack(fill="x", padx=10, pady=(10,4))
        esq = tk.Frame(head, bg=BG2); esq.pack(side="left", fill="x", expand=True)

        if idx_t >= 0:
            ttxt = tk.Frame(esq, bg=BG2); ttxt.pack(anchor="w")
            partes = [(txt[:idx_t], FG, BG2, False), (txt[idx_t:idx_t+len(termo)], "#fff", ACCENT, True), (txt[idx_t+len(termo):], FG, BG2, False)]
            for parte, fg_c, bg_c2, hl in partes:
                if parte:
                    tk.Label(ttxt, text=parte, bg=bg_c2, fg=fg_c, font=FNT_TITLE, padx=(2 if hl else 0)).pack(side="left")
        else:
            tk.Label(esq, text=txt, bg=BG2, fg=FG, font=FNT_TITLE, anchor="w").pack(anchor="w")

        bdg_row = tk.Frame(esq, bg=BG2); bdg_row.pack(anchor="w", pady=(3,0))
        _badge(bdg_row, f"⚑ {prior}", cp, "#fff" if prior!="Média" else "#1e1e2e")
        if cr: _badge(bdg_row, f"🔁 {rep}", cr, "#fff")
        if conc: _badge(bdg_row, "✅ Concluída", FG_OK, "#1e1e2e")
        else: _badge(bdg_row, "⏳ Pendente", ACCENT2, "#fff")

        drow = tk.Frame(body, bg=BG2); drow.pack(fill="x", padx=10, pady=(0,4))
        if item.get("criado_em"): tk.Label(drow, text=f"🕐 Criada: {item['criado_em']}", bg=BG2, fg=FG3, font=FNT_MONO).pack(side="left", padx=(0,14))
        if item.get("concluida_em"): tk.Label(drow, text=f"✅ Concluída: {item['concluida_em']}", bg=BG2, fg=FG_OK, font=FNT_MONO).pack(side="left")

        tk.Frame(body, bg=BG2, height=4).pack()

    # ── Ações ─────────────────────────────────────────────────────────────────
    def _adicionar_tarefa(self):
        texto = self._inp_tarefa.get().strip()
        if not texto: return
        agend = self._inp_agendada.get().strip(); agend_str = ""
        if agend:
            dt = parse_dt(agend)
            if not dt: messagebox.showerror("Formato inválido","Use: DD/MM/AAAA HH:MM"); return
            agend_str = dt.strftime("%d/%m/%Y %H:%M")
        self.tarefas.append(nova_tarefa_dict(texto, self._pri_var.get(), self._rep_var.get(), agend_str))
        self._salvar(); self._inp_tarefa.delete(0,"end"); self._inp_agendada.delete(0,"end")
        self._rep_var.set("Sem repetição"); self._pri_var.set("Média")
        # Resetar visual dos botões
        for v, (btn, cor) in self._rep_btns.items():
            btn.config(bg=BG3 if v != "Sem repetição" else cor,
                       fg="#fff" if v == "Sem repetição" else cor,
                       font=("Segoe UI", 10, "bold") if v == "Sem repetição" else FNT_SMALL)
        for v, (btn, cor) in self._pri_btns.items():
            btn.config(bg=cor if v == "Média" else BG3,
                       fg=("#1e1e2e" if cor == COR_MEDIA else "#fff") if v == "Média" else cor,
                       font=("Segoe UI", 10, "bold") if v == "Média" else FNT_SMALL)
        self._render_lista()

    def _toggle_tarefa(self, idx):
        import copy; t=self.tarefas[idx]; a=agora()
        t["concluida"]=not t["concluida"]; t.setdefault("log",[])
        if t["concluida"]:
            t["concluida_em"]=a; t["log"].append({"evento":"Concluída","quando":a})
            h=next((x for x in self.historico if x["texto"]==t["texto"] and x.get("criado_em")==t.get("criado_em")),None)
            if not h:
                self.historico.append({"texto":t["texto"],"criado_em":t.get("criado_em",a),"concluida_em":a,
                    "repeticao":t.get("repeticao","Sem repetição"),"prioridade":t.get("prioridade","Média"),
                    "log":list(t["log"]),"subtarefas":copy.deepcopy(t.get("subtarefas",[])),
                    "notif_agendada":t.get("notif_agendada","")})
            else: h["concluida_em"]=a; h["log"]=list(t["log"])
            self.historico=purgar_hist(self.historico)
        else: t["concluida_em"]=None; t["log"].append({"evento":"Reaberta","quando":a})
        self._salvar(); self._render_lista()

    def _remover_tarefa(self, idx):
        t=self.tarefas[idx]
        if not t.get("concluida"):
            self.historico=[h for h in self.historico if not(h["texto"]==t["texto"] and h.get("criado_em")==t.get("criado_em"))]
        self.tarefas.pop(idx); self._salvar(); self._render_lista()

    def _limpar_concluidas(self):
        self.tarefas=[t for t in self.tarefas if not t.get("concluida")]; self._salvar(); self._render_lista()

    def _reagendar_notif(self, idx, dt_str):
        """Atualiza a notificação agendada de uma tarefa existente."""
        t = self.tarefas[idx]
        if dt_str:
            dt = parse_dt(dt_str)
            if not dt:
                return
            t["notif_agendada"] = dt.strftime("%d/%m/%Y %H:%M")
            t["notif_disparada"] = False   # permite disparar novamente
        else:
            t["notif_agendada"] = ""
            t["notif_disparada"] = False
        self._salvar()
        self._render_lista()

    def _set_repeticao(self, idx, v):
        self.tarefas[idx]["repeticao"]=v; self._salvar()

    def _set_prioridade(self, idx, v):
        self.tarefas[idx]["prioridade"]=v; self._salvar(); self._render_lista()

    def _reabrir(self, item):
        import copy; a=agora(); log=list(item.get("log",[])); log.append({"evento":"Reaberta","quando":a})
        h=next((x for x in self.historico if x["texto"]==item["texto"] and x.get("criado_em")==item.get("criado_em")),None)
        if h: h["log"]=log; h["concluida_em"]=None
        self.tarefas.append({"texto":item["texto"],"concluida":False,"concluida_em":None,
            "criado_em":item.get("criado_em",a),"repeticao":item.get("repeticao","Sem repetição"),
            "prioridade":item.get("prioridade","Média"),"log":log,
            "subtarefas":copy.deepcopy(item.get("subtarefas",[])),"notif_agendada":"","notif_disparada":False})
        self._salvar(); self._render_lista(); self._render_historico()

    def _toggle_notif(self):
        self.cfg["notificacoes_ligadas"]=not self.cfg["notificacoes_ligadas"]
        if self.cfg["notificacoes_ligadas"]:
            self._btn_toggle.config(text="● Ligadas",bg=FG_OK,activebackground=FG_OK2)
            self._prox_notif=time.time()+self.cfg["intervalo_minutos"]*60
        else: self._btn_toggle.config(text="○ Desligadas",bg=ACCENT2,activebackground=ACCENT2_H)
        self._salvar()

    def _aplicar_intervalo(self):
        try: v=max(1,int(self._inp_intervalo.get()))
        except: v=30
        self.cfg["intervalo_minutos"]=v; self._inp_intervalo.delete(0,"end"); self._inp_intervalo.insert(0,str(v))
        self._prox_notif=time.time()+v*60; self._salvar()

    def _exportar(self):
        path=filedialog.asksaveasfilename(defaultextension=".json",filetypes=[("JSON","*.json")],initialfile="tarefas.json")
        if not path: return
        with open(path,"w",encoding="utf-8") as f:
            json.dump({"tarefas":self.tarefas,"historico":self.historico,"config":self.cfg},f,ensure_ascii=False,indent=2)
        messagebox.showinfo("Exportar",f"Exportado para:\n{path}")

    def _importar(self):
        path=filedialog.askopenfilename(filetypes=[("JSON","*.json")])
        if not path: return
        try:
            with open(path,encoding="utf-8") as f: d=json.load(f)
            if "tarefas" not in d: messagebox.showerror("Erro",'Arquivo inválido: sem campo "tarefas".'); return
            self.tarefas=d.get("tarefas",[]); self.historico=d.get("historico",[]); self.cfg={**self.cfg,**d.get("config",{})}
            self._salvar()
            self._btn_toggle.config(text="● Ligadas" if self.cfg["notificacoes_ligadas"] else "○ Desligadas",
                                     bg=FG_OK if self.cfg["notificacoes_ligadas"] else ACCENT2)
            self._inp_intervalo.delete(0,"end"); self._inp_intervalo.insert(0,str(self.cfg["intervalo_minutos"]))
            self._render_lista()
            messagebox.showinfo("Importar",f"✅ {len(self.tarefas)} tarefa(s), {len(self.historico)} no histórico.")
        except Exception as e: messagebox.showerror("Erro",f"Erro ao ler JSON:\n{e}")

    def _excluir_tudo(self):
        if not messagebox.askyesno("⚠ Zona de Perigo","Apagar TODAS as tarefas e histórico? Sem volta."): return
        self.tarefas=[]; self.historico=[]; self._salvar(); self._render_lista()
        messagebox.showinfo("Pronto","✅ Tudo apagado.")

    # ── Notificações ──────────────────────────────────────────────────────────
    def _textos_visiveis(self):
        """Retorna dict {tipo: texto} com as tarefas atualmente visíveis nos overlays."""
        return {tipo: getattr(w, "_tarefa_texto", None)
                for tipo, w in self._notif_widgets.items()}

    def _loop_notif(self):
        while True:
            time.sleep(5)
            ts = time.time()

            # ── Notificação cíclica ───────────────────────────────────────────
            if self.cfg.get("notificacoes_ligadas") and ts >= self._prox_notif:
                self._prox_notif = ts + self.cfg["intervalo_minutos"] * 60
                pend = [t for t in self.tarefas if not t.get("concluida")]
                if pend:
                    # Ordena por prioridade, depois por data de criação (mais antiga primeiro)
                    urg = sorted(pend,
                                 key=lambda t: (PRIOR_ORD.get(t.get("prioridade", "Média"), 1),
                                                t.get("criado_em", "")))
                    # Pula a tarefa que já está visível em agendada (uma tarefa = um tipo)
                    texto_em_agendada = self._textos_visiveis().get("agendada")
                    candidato = None
                    for t in urg:
                        if t["texto"] != texto_em_agendada:
                            candidato = t
                            break
                    if candidato:
                        td = candidato["texto"]
                        pr = candidato.get("prioridade", "Média")
                        corpo = f"Você tem {len(pend)} tarefa(s) pendente(s)."
                        notificar("⏰ Lembrete Cíclico", f"📌 {td}\n{corpo}", "ciclica")
                        self.after(0, lambda td_=td, c=corpo, p=pr:
                                   self._mostrar_overlay("ciclica", "⏰ Lembrete Cíclico", td_, c, p))

            # ── Notificações agendadas — enfileira todas que dispararam ───────
            novas_na_fila = 0
            for t in self.tarefas:
                if t.get("concluida") or not t.get("notif_agendada") or t.get("notif_disparada"):
                    continue
                dt_alvo = parse_dt(t["notif_agendada"])
                if dt_alvo and datetime.now() >= dt_alvo:
                    t["notif_disparada"] = True
                    self._salvar()
                    self._fila_agendadas.append({
                        "texto":      t["texto"],
                        "prioridade": t.get("prioridade", "Média"),
                        "agendada":   t["notif_agendada"],
                    })
                    novas_na_fila += 1
                    notificar("🔔 Lembrete Agendado", f"📌 {t['texto']}", "agendada")

            if novas_na_fila:
                self.after(0, self._processar_fila_agendadas)

    def _processar_fila_agendadas(self):
        """Exibe a próxima agendada da fila respeitando a regra: uma tarefa por tipo.

        Caso especial — takeover:
          Se o melhor candidato da fila é exatamente a tarefa visível na cíclica,
          a agendada tem prioridade: fecha a cíclica, abre a agendada e dispara
          imediatamente uma nova cíclica com a próxima tarefa elegível.
        """

        # Se já há uma agendada aberta, só atualiza o contador
        if self._notif_aberta.get("agendada"):
            w = self._notif_widgets.get("agendada")
            if w:
                try:
                    w.atualizar_fila(len(self._fila_agendadas))
                    self._reposicionar_overlays()
                except Exception:
                    pass
            return

        if not self._fila_agendadas:
            return

        # Candidato preferencial: primeiro da fila (ordem de chegada)
        item = self._fila_agendadas[0]
        texto_em_ciclica = self._textos_visiveis().get("ciclica")

        if item["texto"] == texto_em_ciclica:
            # ── Takeover: agendada "rouba" o slot da cíclica ─────────────────
            # 1) Fecha a cíclica silenciosamente (sem chamar _processar_fila de novo)
            w_ciclica = self._notif_widgets.get("ciclica")
            if w_ciclica:
                try:
                    self._notif_aberta["ciclica"] = False
                    del self._notif_widgets["ciclica"]
                    w_ciclica.destroy()
                except Exception:
                    pass

            # 2) Abre a agendada normalmente
            corpo = f"Agendada para {item['agendada']}"
            self._mostrar_overlay("agendada", "🔔 Lembrete Agendado",
                                  item["texto"], corpo, item["prioridade"],
                                  fila_total=len(self._fila_agendadas))

            # 3) Dispara nova cíclica com a próxima tarefa elegível
            #    (maior prioridade + mais antiga, diferente da agendada recém-aberta)
            self.after(100, self._disparar_proxima_ciclica)
            return

        # Caso normal: candidato não conflita com a cíclica — exibe direto
        fila_total = len(self._fila_agendadas)
        corpo = f"Agendada para {item['agendada']}"
        self._mostrar_overlay("agendada", "🔔 Lembrete Agendado",
                              item["texto"], corpo, item["prioridade"], fila_total=fila_total)

    def _disparar_proxima_ciclica(self):
        """Abre uma cíclica com a tarefa pendente de maior prioridade mais antiga,
        excluindo qualquer tarefa já visível na agendada aberta no momento."""
        if self._notif_aberta.get("ciclica"):
            return  # já há uma cíclica aberta

        texto_em_agendada = self._textos_visiveis().get("agendada")
        pend = [t for t in self.tarefas if not t.get("concluida")]
        if not pend:
            return

        urg = sorted(pend,
                     key=lambda t: (PRIOR_ORD.get(t.get("prioridade", "Média"), 1),
                                    t.get("criado_em", "")))
        candidato = None
        for t in urg:
            if t["texto"] != texto_em_agendada:
                candidato = t
                break

        if candidato:
            td = candidato["texto"]
            pr = candidato.get("prioridade", "Média")
            corpo = f"Você tem {len(pend)} tarefa(s) pendente(s)."
            notificar("⏰ Lembrete Cíclico", f"📌 {td}\n{corpo}", "ciclica")
            self._mostrar_overlay("ciclica", "⏰ Lembrete Cíclico", td, corpo, pr)

    def _mostrar_overlay(self, tipo, titulo, tarefa_texto, corpo, prioridade="Média", fila_total=0):
        """Exibe overlay. Máx 1 por tipo. Garante que cada tarefa apareça em apenas um tipo."""
        if self._notif_aberta.get(tipo):
            return

        self._notif_aberta[tipo] = True

        def ao_fechar(t):
            self._notif_aberta[t] = False
            if t in self._notif_widgets:
                del self._notif_widgets[t]
            if t == "agendada" and self._fila_agendadas:
                self._fila_agendadas.pop(0)
            self._reposicionar_overlays()
            # Ao fechar qualquer tipo, tenta exibir agendadas que estavam bloqueadas
            self.after(200, self._processar_fila_agendadas)

        overlay = NotifOverlay(self, titulo, tarefa_texto, corpo, tipo, ao_fechar,
                               prioridade, fila_total=fila_total)
        self._notif_widgets[tipo] = overlay
        self._reposicionar_overlays()

    def _reposicionar_overlays(self):
        """Empilha notificações ativas ordenadas por prioridade: maior prioridade sempre acima."""
        MARGEM_X = 14
        GAP      = 8

        self.update_idletasks()
        sh = self.winfo_screenheight()
        try:
            import ctypes
            rc = ctypes.wintypes.RECT()
            ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(rc), 0)
            area_util_bottom = rc.bottom
        except Exception:
            area_util_bottom = sh - 48

        MARGEM_Y = 10
        y_atual  = area_util_bottom - MARGEM_Y

        # Ordena widgets ativos: menor PRIOR_ORD = maior prioridade → fica no topo (acima)
        widgets_ativos = list(self._notif_widgets.items())   # [(tipo, overlay), ...]
        widgets_ativos.sort(
            key=lambda kv: PRIOR_ORD.get(getattr(kv[1], "prioridade", "Média"), 1),
            reverse=True   # prioridade mais baixa (Baixa) empilha embaixo; Alta fica acima
        )

        for _tipo, w in widgets_ativos:
            try:
                h     = w.get_altura()
                y_pos = y_atual - h
                w.posicionar(MARGEM_X, y_pos)
                y_atual = y_pos - GAP
            except Exception:
                pass

    # ── Tick (countdown) ─────────────────────────────────────────────────────
    def _tick(self):
        if self.cfg.get("notificacoes_ligadas"):
            rest = max(0, int(self._prox_notif - time.time()))
            mm, ss = divmod(rest, 60); txt = f"⏰ Próxima notificação: {mm:02d}:{ss:02d}"
        else:
            txt = "○ Notificações desligadas"
        self._lbl_countdown.config(text=txt)
        if hasattr(self, "_lbl_cd_opc"): self._lbl_cd_opc.config(text=txt)
        self.after(1000, self._tick)

if __name__ == "__main__":
    App().mainloop()
