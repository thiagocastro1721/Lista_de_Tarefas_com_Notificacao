import tkinter as tk
import threading
import time
import json
import os
from datetime import datetime, timedelta

ARQUIVO_TAREFAS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tarefas.json")
INTERVALO_NOTIFICACAO = 30 * 60
DIAS_HISTORICO = 30

# ─── Paleta ───────────────────────────────────────────────────────────────────
BG          = "#1e1e2e"
BG2         = "#2a2a3d"
HEADER      = "#13131f"
ENTRADA_BG  = "#2e2e45"
BORDA       = "#3a3a55"
ACCENT      = "#7c6af7"
ACCENT2     = "#e74c3c"
FG          = "#e2e2f0"
FG2         = "#8888aa"
FG_OK       = "#4caf82"
FG_WARN     = "#f39c12"
TAB_ATIVA   = "#7c6af7"
TAB_INATIVA = "#2a2a3d"
COR_DIARIO  = "#3a6baf"   # azul — indicador de repetição diária
COR_SEMANAL = "#7a3faf"   # roxo escuro — repetição semanal

REPETICOES = ["Sem repetição", "Diariamente", "Semanalmente"]

# ─── Persistência ─────────────────────────────────────────────────────────────

def carregar_dados():
    if os.path.exists(ARQUIVO_TAREFAS):
        with open(ARQUIVO_TAREFAS, "r", encoding="utf-8") as f:
            dados = json.load(f)
        if isinstance(dados, list):
            return {"tarefas": dados, "historico": []}
        return dados
    return {"tarefas": [], "historico": []}

def salvar_dados(tarefas, historico, config=None):
    with open(ARQUIVO_TAREFAS, "w", encoding="utf-8") as f:
        json.dump({"tarefas": tarefas, "historico": historico,
                   "config": config or {}}, f, ensure_ascii=False, indent=2)

def purgar_historico(historico):
    """Mantém apenas entradas cujo evento mais recente tem <= 30 dias."""
    limite = datetime.now() - timedelta(days=DIAS_HISTORICO)
    resultado = []
    for h in historico:
        log = h.get("log", [])
        ultima = log[-1]["quando"] if log else h.get("concluida_em", "")
        if _parse_data(ultima) >= limite:
            resultado.append(h)
    return resultado

def _parse_data(s):
    try:
        return datetime.strptime(s, "%d/%m/%Y %H:%M")
    except Exception:
        return datetime.min

# ─── App ──────────────────────────────────────────────────────────────────────

class AppTarefas:
    def __init__(self, root):
        self.root = root
        self.root.title("📝 Lista de Tarefas")
        self.root.geometry("540x680")
        self.root.resizable(False, True)
        self.root.configure(bg=BG)

        try:
            from ctypes import windll, byref, sizeof, c_int
            HWND = windll.user32.GetParent(self.root.winfo_id())
            windll.dwmapi.DwmSetWindowAttribute(HWND, 20, byref(c_int(1)), sizeof(c_int))
        except Exception:
            pass

        dados = carregar_dados()
        self.tarefas   = dados.get("tarefas", [])
        self.historico = purgar_historico(dados.get("historico", []))

        for t in self.tarefas:
            if "criado_em" not in t:
                t["criado_em"] = datetime.now().strftime("%d/%m/%Y %H:%M")
            if "repeticao" not in t:
                t["repeticao"] = "Sem repetição"

        cfg = dados.get("config", {})
        self.notificacao_ativa      = True
        self.notificacoes_ligadas   = cfg.get("notificacoes_ligadas", True)
        self.intervalo_minutos      = cfg.get("intervalo_minutos", 30)
        self._popup_aberto          = False
        self.tempo_prox_notificacao = time.time() + self.intervalo_minutos * 60
        self._aba_atual             = "tarefas"

        self._construir_interface()
        self._verificar_repeticoes()
        self._atualizar_lista()
        self._iniciar_thread_notificacao()
        self.root.protocol("WM_DELETE_WINDOW", self._ao_fechar)

    # ─── Interface ────────────────────────────────────────────────────────────

    def _construir_interface(self):
        header = tk.Frame(self.root, bg=HEADER, pady=14)
        header.pack(fill=tk.X)
        tk.Label(header, text="📝 Lista de Tarefas", font=("Segoe UI", 17, "bold"),
                 bg=HEADER, fg=FG).pack()

        abas_frame = tk.Frame(self.root, bg=BG)
        abas_frame.pack(fill=tk.X)
        self.btn_aba_tarefas = tk.Button(
            abas_frame, text="Tarefas", font=("Segoe UI", 10, "bold"),
            bg=TAB_ATIVA, fg="white", relief=tk.FLAT, cursor="hand2",
            padx=18, pady=6, activebackground=ACCENT, activeforeground="white",
            command=lambda: self._mudar_aba("tarefas"))
        self.btn_aba_tarefas.pack(side=tk.LEFT)
        self.btn_aba_historico = tk.Button(
            abas_frame, text="Histórico (30 dias)", font=("Segoe UI", 10),
            bg=TAB_INATIVA, fg=FG2, relief=tk.FLAT, cursor="hand2",
            padx=18, pady=6, activebackground=ACCENT, activeforeground="white",
            command=lambda: self._mudar_aba("historico"))
        self.btn_aba_historico.pack(side=tk.LEFT)
        self.btn_aba_pesquisa = tk.Button(
            abas_frame, text="🔍 Pesquisar", font=("Segoe UI", 10),
            bg=TAB_INATIVA, fg=FG2, relief=tk.FLAT, cursor="hand2",
            padx=18, pady=6, activebackground=ACCENT, activeforeground="white",
            command=lambda: self._mudar_aba("pesquisa"))
        self.btn_aba_pesquisa.pack(side=tk.LEFT)
        tk.Frame(self.root, height=1, bg=BORDA).pack(fill=tk.X)

        self.frame_principal = tk.Frame(self.root, bg=BG)
        self.frame_principal.pack(fill=tk.BOTH, expand=True)

        self._construir_aba_tarefas()
        self._construir_aba_historico()
        self._construir_aba_pesquisa()
        self.frame_tarefas_aba.pack(fill=tk.BOTH, expand=True)

    def _construir_aba_tarefas(self):
        self.frame_tarefas_aba = tk.Frame(self.frame_principal, bg=BG)

        # Linha de entrada + repetição
        entrada_outer = tk.Frame(self.frame_tarefas_aba, bg=BG, pady=10, padx=16)
        entrada_outer.pack(fill=tk.X)

        # Linha 1: campo de texto + botão
        linha1 = tk.Frame(entrada_outer, bg=BG)
        linha1.pack(fill=tk.X)
        self.entrada = tk.Entry(linha1, font=("Segoe UI", 12), relief=tk.FLAT,
                                bd=0, bg=ENTRADA_BG, fg=FG, insertbackground=FG)
        self.entrada.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=8, ipadx=8, padx=(0, 8))
        self.entrada.bind("<Return>", lambda e: self._adicionar_tarefa())
        tk.Button(linha1, text="Adicionar", font=("Segoe UI", 11, "bold"),
                  bg=ACCENT, fg="white", relief=tk.FLAT, cursor="hand2",
                  padx=12, pady=6, activebackground="#6a5ae0", activeforeground="white",
                  command=self._adicionar_tarefa).pack(side=tk.RIGHT)

        # Linha 2: seletor de repetição
        linha2 = tk.Frame(entrada_outer, bg=BG)
        linha2.pack(fill=tk.X, pady=(6, 0))
        tk.Label(linha2, text="Repetir:", font=("Segoe UI", 9),
                 bg=BG, fg=FG2).pack(side=tk.LEFT)

        self.var_repeticao = tk.StringVar(value="Sem repetição")
        for opcao in REPETICOES:
            cor = {"Sem repetição": FG2, "Diariamente": COR_DIARIO, "Semanalmente": COR_SEMANAL}[opcao]
            rb = tk.Radiobutton(linha2, text=opcao, variable=self.var_repeticao, value=opcao,
                                font=("Segoe UI", 9), bg=BG, fg=cor, selectcolor=BG2,
                                activebackground=BG, activeforeground=cor,
                                cursor="hand2", bd=0, highlightthickness=0)
            rb.pack(side=tk.LEFT, padx=(10, 0))

        self.status_label = tk.Label(self.frame_tarefas_aba, text="", font=("Segoe UI", 10),
                                     bg=BG, fg=FG2)
        self.status_label.pack(anchor="w", padx=16)
        tk.Frame(self.frame_tarefas_aba, height=1, bg=BORDA).pack(fill=tk.X, padx=16, pady=2)

        lista_frame = tk.Frame(self.frame_tarefas_aba, bg=BG)
        lista_frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=6)
        scrollbar = tk.Scrollbar(lista_frame, troughcolor=BG2, bg=BORDA)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas = tk.Canvas(lista_frame, bg=BG, bd=0,
                                highlightthickness=0, yscrollcommand=scrollbar.set)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.canvas.yview)
        self.frame_lista = tk.Frame(self.canvas, bg=BG)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.frame_lista, anchor="nw")
        self.frame_lista.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.bind("<Enter>", lambda e: self.canvas.bind_all("<MouseWheel>", self._on_mousewheel))
        self.canvas.bind("<Leave>", lambda e: self.canvas.unbind_all("<MouseWheel>"))

        # Linha 1: botão limpar + contador
        rodape = tk.Frame(self.frame_tarefas_aba, bg=BG, pady=4)
        rodape.pack(fill=tk.X, padx=16)
        tk.Button(rodape, text="🧹 Limpar concluídas", font=("Segoe UI", 10),
                  bg=BG2, fg=FG2, relief=tk.FLAT, cursor="hand2",
                  padx=10, pady=5, activebackground=BORDA, activeforeground=FG,
                  command=self._limpar_concluidas).pack(side=tk.LEFT)
        self.label_prox = tk.Label(rodape, text="", font=("Segoe UI", 9), bg=BG, fg=FG2)
        self.label_prox.pack(side=tk.RIGHT)

        # Linha 2: configurações de notificação
        cfg_frame = tk.Frame(self.frame_tarefas_aba, bg=BG2, pady=6, padx=14)
        cfg_frame.pack(fill=tk.X, padx=16, pady=(0, 8))

        # Toggle ligar/desligar
        self.var_notif = tk.BooleanVar(value=self.notificacoes_ligadas)
        tk.Label(cfg_frame, text="🔔 Notificações:", font=("Segoe UI", 9),
                 bg=BG2, fg=FG2).pack(side=tk.LEFT)
        self.btn_notif_toggle = tk.Button(
            cfg_frame, text="● Ligadas" if self.notificacoes_ligadas else "○ Desligadas",
            font=("Segoe UI", 9, "bold"),
            bg=FG_OK if self.notificacoes_ligadas else ACCENT2,
            fg="white", relief=tk.FLAT, cursor="hand2", padx=8, pady=2,
            command=self._toggle_notificacoes)
        self.btn_notif_toggle.pack(side=tk.LEFT, padx=(6, 16))

        # Intervalo
        tk.Label(cfg_frame, text="Intervalo:", font=("Segoe UI", 9),
                 bg=BG2, fg=FG2).pack(side=tk.LEFT)
        self.var_intervalo = tk.StringVar(value=str(self.intervalo_minutos))
        vcmd = (self.root.register(lambda s: s.isdigit() and len(s) <= 3 or s == ""), "%P")
        self.entry_intervalo = tk.Entry(
            cfg_frame, textvariable=self.var_intervalo,
            font=("Segoe UI", 9), width=4, relief=tk.FLAT,
            bg=ENTRADA_BG, fg=FG, insertbackground=FG,
            justify="center", validate="key", validatecommand=vcmd)
        self.entry_intervalo.pack(side=tk.LEFT, padx=(6, 4), ipady=3)
        tk.Label(cfg_frame, text="min", font=("Segoe UI", 9),
                 bg=BG2, fg=FG2).pack(side=tk.LEFT)
        tk.Button(cfg_frame, text="Aplicar", font=("Segoe UI", 9),
                  bg=ACCENT, fg="white", relief=tk.FLAT, cursor="hand2",
                  padx=8, pady=2, activebackground="#6a5ae0",
                  command=self._aplicar_intervalo).pack(side=tk.LEFT, padx=(8, 0))

    def _construir_aba_historico(self):
        self.frame_historico_aba = tk.Frame(self.frame_principal, bg=BG)
        tk.Label(self.frame_historico_aba,
                 text="Tarefas concluídas nos últimos 30 dias",
                 font=("Segoe UI", 10), bg=BG, fg=FG2).pack(anchor="w", padx=16, pady=(10, 4))
        tk.Frame(self.frame_historico_aba, height=1, bg=BORDA).pack(fill=tk.X, padx=16, pady=2)

        hist_frame = tk.Frame(self.frame_historico_aba, bg=BG)
        hist_frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=6)
        scrollbar_h = tk.Scrollbar(hist_frame, troughcolor=BG2, bg=BORDA)
        scrollbar_h.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas_hist = tk.Canvas(hist_frame, bg=BG, bd=0,
                                     highlightthickness=0, yscrollcommand=scrollbar_h.set)
        self.canvas_hist.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_h.config(command=self.canvas_hist.yview)
        self.frame_hist_lista = tk.Frame(self.canvas_hist, bg=BG)
        self.canvas_hist_window = self.canvas_hist.create_window(
            (0, 0), window=self.frame_hist_lista, anchor="nw")
        self.frame_hist_lista.bind("<Configure>",
            lambda e: self.canvas_hist.configure(scrollregion=self.canvas_hist.bbox("all")))
        self.canvas_hist.bind("<Configure>",
            lambda e: self.canvas_hist.itemconfig(self.canvas_hist_window, width=e.width))
        self.canvas_hist.bind("<Enter>",
            lambda e: self.canvas_hist.bind_all("<MouseWheel>", self._on_mousewheel_hist))
        self.canvas_hist.bind("<Leave>",
            lambda e: self.canvas_hist.unbind_all("<MouseWheel>"))

    def _construir_aba_pesquisa(self):
        self.frame_pesquisa_aba = tk.Frame(self.frame_principal, bg=BG)

        # Campo de busca
        busca_frame = tk.Frame(self.frame_pesquisa_aba, bg=BG, pady=10, padx=16)
        busca_frame.pack(fill=tk.X)
        self.entrada_pesquisa = tk.Entry(busca_frame, font=("Segoe UI", 12), relief=tk.FLAT,
                                         bd=0, bg=ENTRADA_BG, fg=FG, insertbackground=FG)
        self.entrada_pesquisa.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=8, ipadx=8, padx=(0, 8))
        self.entrada_pesquisa.bind("<Return>", lambda e: self._executar_pesquisa())
        self.entrada_pesquisa.bind("<KeyRelease>", lambda e: self._executar_pesquisa())
        tk.Button(busca_frame, text="🔍", font=("Segoe UI", 12), bg=ACCENT, fg="white",
                  relief=tk.FLAT, cursor="hand2", padx=10, pady=5,
                  activebackground="#6a5ae0", activeforeground="white",
                  command=self._executar_pesquisa).pack(side=tk.RIGHT)

        self.label_pesquisa_status = tk.Label(self.frame_pesquisa_aba, text="Digite para pesquisar…",
                                               font=("Segoe UI", 9), bg=BG, fg=FG2)
        self.label_pesquisa_status.pack(anchor="w", padx=16)
        tk.Frame(self.frame_pesquisa_aba, height=1, bg=BORDA).pack(fill=tk.X, padx=16, pady=2)

        # Área de resultados com scroll
        res_frame = tk.Frame(self.frame_pesquisa_aba, bg=BG)
        res_frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=6)
        sb = tk.Scrollbar(res_frame, troughcolor=BG2, bg=BORDA)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas_pesq = tk.Canvas(res_frame, bg=BG, bd=0,
                                     highlightthickness=0, yscrollcommand=sb.set)
        self.canvas_pesq.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.config(command=self.canvas_pesq.yview)
        self.frame_pesq_lista = tk.Frame(self.canvas_pesq, bg=BG)
        self._pesq_win = self.canvas_pesq.create_window((0, 0), window=self.frame_pesq_lista, anchor="nw")
        self.frame_pesq_lista.bind("<Configure>",
            lambda e: self.canvas_pesq.configure(scrollregion=self.canvas_pesq.bbox("all")))
        self.canvas_pesq.bind("<Configure>",
            lambda e: self.canvas_pesq.itemconfig(self._pesq_win, width=e.width))
        self.canvas_pesq.bind("<Enter>",
            lambda e: self.canvas_pesq.bind_all("<MouseWheel>",
                lambda ev: self.canvas_pesq.yview_scroll(int(-1*(ev.delta/120)), "units")))
        self.canvas_pesq.bind("<Leave>",
            lambda e: self.canvas_pesq.unbind_all("<MouseWheel>"))

    def _executar_pesquisa(self):
        for w in self.frame_pesq_lista.winfo_children():
            w.destroy()

        termo = self.entrada_pesquisa.get().strip().lower()
        if not termo:
            self.label_pesquisa_status.config(text="Digite para pesquisar…")
            return

        # Monta pool: tarefas ativas + histórico (sem duplicar pela chave criado_em+texto)
        pool = {}
        for t in self.tarefas:
            chave = (t["texto"], t.get("criado_em", ""))
            if chave not in pool:
                pool[chave] = {
                    "texto": t["texto"],
                    "criado_em": t.get("criado_em", ""),
                    "concluida_em": t.get("concluida_em"),
                    "repeticao": t.get("repeticao", "Sem repetição"),
                    "log": t.get("log", []),
                    "concluida": t["concluida"]
                }
        for h in self.historico:
            chave = (h["texto"], h.get("criado_em", ""))
            if chave not in pool:
                pool[chave] = {
                    "texto": h["texto"],
                    "criado_em": h.get("criado_em", ""),
                    "concluida_em": h.get("concluida_em"),
                    "repeticao": h.get("repeticao", "Sem repetição"),
                    "log": h.get("log", []),
                    "concluida": bool(h.get("concluida_em"))
                }

        resultados = [v for v in pool.values() if termo in v["texto"].lower()]
        resultados.sort(key=lambda r: _parse_data(
            r["log"][-1]["quando"] if r["log"] else r.get("criado_em", "")), reverse=True)

        total = len(resultados)
        self.label_pesquisa_status.config(
            text=f'{total} resultado(s) para "{self.entrada_pesquisa.get().strip()}"')

        if not resultados:
            tk.Label(self.frame_pesq_lista, text="Nenhuma tarefa encontrada.",
                     font=("Segoe UI", 11), bg=BG, fg=FG2).pack(pady=30)
            return

        ICONES = {"Criada": ("🕐", FG2), "Concluída": ("✅", FG_OK), "Reaberta": ("↩", FG_WARN)}
        for item in resultados:
            log  = item.get("log", [])
            rep  = item.get("repeticao", "Sem repetição")
            pendente = not item["concluida"]

            card = tk.Frame(self.frame_pesq_lista, bg=BG2, bd=0, pady=6, padx=10,
                            highlightbackground=BORDA, highlightthickness=1)
            card.pack(fill=tk.X, pady=4)

            # Cabeçalho
            topo = tk.Frame(card, bg=BG2)
            topo.pack(fill=tk.X)
            badge_cor = {"Sem repetição": None, "Diariamente": COR_DIARIO,
                         "Semanalmente": COR_SEMANAL}[rep]
            if badge_cor:
                tk.Label(topo, text=f" 🔁 {rep} ", font=("Segoe UI", 7),
                         bg=badge_cor, fg="white").pack(side=tk.RIGHT, padx=(4, 0))
            if pendente:
                tk.Label(topo, text=" pendente ", font=("Segoe UI", 7),
                         bg=ACCENT2, fg="white").pack(side=tk.RIGHT, padx=(4, 0))
            else:
                tk.Label(topo, text=" concluída ", font=("Segoe UI", 7),
                         bg=FG_OK, fg="#1e1e2e").pack(side=tk.RIGHT, padx=(4, 0))

            # Destaca termo pesquisado no título
            texto = item["texto"]
            idx_low = texto.lower().find(termo)
            lbl_frame = tk.Frame(topo, bg=BG2)
            lbl_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
            if idx_low >= 0:
                antes = texto[:idx_low]
                match = texto[idx_low:idx_low+len(termo)]
                depois = texto[idx_low+len(termo):]
                if antes:
                    tk.Label(lbl_frame, text=antes, font=("Segoe UI", 11, "bold"),
                             bg=BG2, fg=FG).pack(side=tk.LEFT)
                tk.Label(lbl_frame, text=match, font=("Segoe UI", 11, "bold"),
                         bg=ACCENT, fg="white").pack(side=tk.LEFT)
                if depois:
                    tk.Label(lbl_frame, text=depois, font=("Segoe UI", 11, "bold"),
                             bg=BG2, fg=FG).pack(side=tk.LEFT)
            else:
                tk.Label(lbl_frame, text=texto, font=("Segoe UI", 11, "bold"),
                         bg=BG2, fg=FG).pack(side=tk.LEFT)

            # Separador
            tk.Frame(card, height=1, bg=BORDA).pack(fill=tk.X, pady=(4, 2))

            # Log de eventos
            if not log and (item.get("criado_em") or item.get("concluida_em")):
                log = []
                if item.get("criado_em"):
                    log.append({"evento": "Criada", "quando": item["criado_em"]})
                if item.get("concluida_em"):
                    log.append({"evento": "Concluída", "quando": item["concluida_em"]})

            if log:
                for entrada in log:
                    icone, cor = ICONES.get(entrada["evento"], ("•", FG2))
                    linha_log = tk.Frame(card, bg=BG2)
                    linha_log.pack(fill=tk.X, pady=1)
                    tk.Label(linha_log, text=icone, font=("Segoe UI", 9),
                             bg=BG2, fg=cor, width=2).pack(side=tk.LEFT)
                    tk.Label(linha_log, text=entrada["evento"],
                             font=("Segoe UI", 9, "bold"), bg=BG2, fg=cor,
                             width=10, anchor="w").pack(side=tk.LEFT)
                    tk.Label(linha_log, text=entrada["quando"],
                             font=("Segoe UI", 9), bg=BG2, fg=FG2,
                             anchor="w").pack(side=tk.LEFT)
            else:
                tk.Label(card, text="  Sem log registrado", font=("Segoe UI", 8),
                         bg=BG2, fg=FG2).pack(anchor="w")

    def _mudar_aba(self, aba):
        self._aba_atual = aba
        # Esconde todos os frames
        for f in (self.frame_tarefas_aba, self.frame_historico_aba, self.frame_pesquisa_aba):
            f.pack_forget()
        # Reseta todos os botões
        self.btn_aba_tarefas.config(bg=TAB_INATIVA, fg=FG2, font=("Segoe UI", 10))
        self.btn_aba_historico.config(bg=TAB_INATIVA, fg=FG2, font=("Segoe UI", 10))
        self.btn_aba_pesquisa.config(bg=TAB_INATIVA, fg=FG2, font=("Segoe UI", 10))
        if aba == "tarefas":
            self.frame_tarefas_aba.pack(fill=tk.BOTH, expand=True)
            self.btn_aba_tarefas.config(bg=TAB_ATIVA, fg="white", font=("Segoe UI", 10, "bold"))
        elif aba == "historico":
            self.frame_historico_aba.pack(fill=tk.BOTH, expand=True)
            self.btn_aba_historico.config(bg=TAB_ATIVA, fg="white", font=("Segoe UI", 10, "bold"))
            self._atualizar_historico()
        else:
            self.frame_pesquisa_aba.pack(fill=tk.BOTH, expand=True)
            self.btn_aba_pesquisa.config(bg=TAB_ATIVA, fg="white", font=("Segoe UI", 10, "bold"))
            self.entrada_pesquisa.focus_set()

    def _on_frame_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self.canvas_window, width=event.width)

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_mousewheel_hist(self, event):
        self.canvas_hist.yview_scroll(int(-1 * (event.delta / 120)), "units")

    # ─── Checkbox desenhado ───────────────────────────────────────────────────

    def _desenhar_checkbox(self, cv, marcado):
        cv.delete("all")
        if marcado:
            cv.create_rectangle(2, 2, 20, 20, fill=ACCENT, outline=ACCENT, width=0)
            cv.create_line(5, 11, 9, 16, width=2, fill="white", capstyle=tk.ROUND, joinstyle=tk.ROUND)
            cv.create_line(9, 16, 17, 6, width=2, fill="white", capstyle=tk.ROUND, joinstyle=tk.ROUND)
        else:
            cv.create_rectangle(2, 2, 20, 20, fill=ENTRADA_BG, outline=BORDA, width=1)

    # ─── Repetição ────────────────────────────────────────────────────────────

    def _verificar_repeticoes(self):
        """Ao iniciar, recria tarefas repetidas que deveriam ter voltado."""
        hoje = datetime.now().date()
        novas = []
        for t in self.tarefas:
            rep = t.get("repeticao", "Sem repetição")
            if rep == "Sem repetição" or not t.get("concluida") or not t.get("concluida_em"):
                continue
            data_conclusao = _parse_data(t["concluida_em"]).date()
            if rep == "Diariamente" and data_conclusao < hoje:
                novas.append(self._clonar_pendente(t))
            elif rep == "Semanalmente" and (hoje - data_conclusao).days >= 7:
                novas.append(self._clonar_pendente(t))
        if novas:
            self.tarefas.extend(novas)
            salvar_dados(self.tarefas, self.historico)

    def _clonar_pendente(self, t):
        return {
            "texto": t["texto"],
            "concluida": False,
            "concluida_em": None,
            "criado_em": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "repeticao": t.get("repeticao", "Sem repetição")
        }

    # ─── Tarefas ──────────────────────────────────────────────────────────────

    def _adicionar_tarefa(self):
        texto = self.entrada.get().strip()
        if not texto:
            return
        agora = datetime.now().strftime("%d/%m/%Y %H:%M")
        self.tarefas.append({
            "texto": texto,
            "concluida": False,
            "concluida_em": None,
            "criado_em": agora,
            "repeticao": self.var_repeticao.get(),
            "log": [{"evento": "Criada", "quando": agora}]
        })
        salvar_dados(self.tarefas, self.historico)
        self.entrada.delete(0, tk.END)
        self.var_repeticao.set("Sem repetição")
        self._atualizar_lista()

    def _toggle_tarefa(self, idx):
        tarefa = self.tarefas[idx]
        agora = datetime.now().strftime("%d/%m/%Y %H:%M")
        tarefa["concluida"] = not tarefa["concluida"]
        if "log" not in tarefa:
            tarefa["log"] = [{"evento": "Criada", "quando": tarefa.get("criado_em", agora)}]
        if tarefa["concluida"]:
            tarefa["concluida_em"] = agora
            tarefa["log"].append({"evento": "Concluída", "quando": agora})
            # Localiza ou cria entrada no histórico para esta tarefa
            entrada = next((h for h in self.historico
                            if h.get("criado_em") == tarefa.get("criado_em")
                            and h["texto"] == tarefa["texto"]), None)
            if entrada is None:
                entrada = {
                    "texto": tarefa["texto"],
                    "criado_em": tarefa.get("criado_em", agora),
                    "concluida_em": agora,
                    "repeticao": tarefa.get("repeticao", "Sem repetição"),
                    "log": list(tarefa["log"])
                }
                self.historico.append(entrada)
            else:
                entrada["concluida_em"] = agora
                entrada["log"] = list(tarefa["log"])
            self.historico = purgar_historico(self.historico)
        else:
            tarefa["concluida_em"] = None
            tarefa["log"].append({"evento": "Reaberta", "quando": agora})
            # Atualiza log no histórico sem remover a entrada
            for h in self.historico:
                if h.get("criado_em") == tarefa.get("criado_em") and h["texto"] == tarefa["texto"]:
                    h["log"] = list(tarefa["log"])
                    h["concluida_em"] = None
                    break
        salvar_dados(self.tarefas, self.historico)
        self._atualizar_lista()

    def _alterar_repeticao(self, idx, valor):
        self.tarefas[idx]["repeticao"] = valor
        salvar_dados(self.tarefas, self.historico)
        self._atualizar_lista()

    def _remover_tarefa(self, idx):
        del self.tarefas[idx]
        salvar_dados(self.tarefas, self.historico)
        self._atualizar_lista()

    def _limpar_concluidas(self):
        self.tarefas = [t for t in self.tarefas if not t["concluida"]]
        salvar_dados(self.tarefas, self.historico)
        self._atualizar_lista()

    def _pendentes(self):
        return sum(1 for t in self.tarefas if not t["concluida"])

    def _atualizar_lista(self):
        for widget in self.frame_lista.winfo_children():
            widget.destroy()

        pendentes = self._pendentes()
        total = len(self.tarefas)
        self.status_label.config(text=f"{pendentes} pendente(s) · {total} no total")

        if not self.tarefas:
            tk.Label(self.frame_lista, text="Nenhuma tarefa ainda. Adicione uma acima!",
                     font=("Segoe UI", 11), bg=BG, fg=FG2).pack(pady=30)
        else:
            for i, tarefa in enumerate(self.tarefas):
                self._criar_item_tarefa(i, tarefa)

        self._atualizar_contador_label()

    def _criar_item_tarefa(self, idx, tarefa):
        concluida    = tarefa["concluida"]
        concluida_em = tarefa.get("concluida_em")
        rep          = tarefa.get("repeticao", "Sem repetição")
        cor_card     = BG2
        cor_texto    = FG2 if concluida else FG
        fonte_texto  = ("Segoe UI", 11, "overstrike") if concluida else ("Segoe UI", 11)

        card = tk.Frame(self.frame_lista, bg=cor_card, bd=0, pady=6, padx=10,
                        highlightbackground=BORDA, highlightthickness=1)
        card.pack(fill=tk.X, pady=3)

        # ── Linha 1: checkbox + texto + botão excluir ──
        linha_topo = tk.Frame(card, bg=cor_card)
        linha_topo.pack(fill=tk.X)

        chk_cv = tk.Canvas(linha_topo, width=22, height=22, bg=cor_card,
                           highlightthickness=0, cursor="hand2")
        chk_cv.pack(side=tk.LEFT, padx=(0, 2))
        self._desenhar_checkbox(chk_cv, concluida)
        chk_cv.bind("<Button-1>", lambda e, i=idx: self._toggle_tarefa(i))

        lbl = tk.Label(linha_topo, text=tarefa["texto"], font=fonte_texto, bg=cor_card,
                       fg=cor_texto, anchor="w", wraplength=310, justify="left")
        lbl.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)

        btn_del = tk.Button(linha_topo, text="✕", font=("Segoe UI", 10), bg=cor_card,
                            fg=ACCENT2, relief=tk.FLAT, cursor="hand2",
                            activebackground=cor_card, activeforeground="#ff6b6b",
                            command=lambda i=idx: self._remover_tarefa(i))
        btn_del.pack(side=tk.RIGHT)

        # ── Linha 2: repetição ──
        linha_rep = tk.Frame(card, bg=cor_card)
        linha_rep.pack(fill=tk.X, pady=(3, 0))

        tk.Label(linha_rep, text="🔁", font=("Segoe UI", 8),
                 bg=cor_card, fg=FG2).pack(side=tk.LEFT, padx=(26, 2))

        var_rep = tk.StringVar(value=rep)
        for opcao in REPETICOES:
            cor = {"Sem repetição": FG2, "Diariamente": COR_DIARIO, "Semanalmente": COR_SEMANAL}[opcao]
            rb = tk.Radiobutton(
                linha_rep, text=opcao, variable=var_rep, value=opcao,
                font=("Segoe UI", 8), bg=cor_card, fg=cor,
                selectcolor=BG, activebackground=cor_card, activeforeground=cor,
                cursor="hand2", bd=0, highlightthickness=0,
                command=lambda v=var_rep, i=idx: self._alterar_repeticao(i, v.get()))
            rb.pack(side=tk.LEFT, padx=(0, 6))

        # ── Linha 3: data de conclusão (se concluída) ──
        if concluida and concluida_em:
            tk.Label(card, text=f"  ✅ Concluída em {concluida_em}",
                     font=("Segoe UI", 8), bg=cor_card, fg=FG_OK,
                     anchor="w").pack(fill=tk.X, padx=4, pady=(2, 0))

    # ─── Histórico ────────────────────────────────────────────────────────────

    def _atualizar_historico(self):
        for widget in self.frame_hist_lista.winfo_children():
            widget.destroy()

        # Ordena pelo evento mais recente do log (ou criado_em)
        def chave_ord(h):
            log = h.get("log", [])
            return _parse_data(log[-1]["quando"]) if log else _parse_data(h.get("criado_em", ""))

        hist = sorted(self.historico, key=chave_ord, reverse=True)

        if not hist:
            tk.Label(self.frame_hist_lista,
                     text="Nenhuma tarefa nos últimos 30 dias.",
                     font=("Segoe UI", 11), bg=BG, fg=FG2).pack(pady=30)
            return

        ICONES = {"Criada": ("🕐", FG2), "Concluída": ("✅", FG_OK),
                  "Reaberta": ("↩", FG_WARN)}

        for item in hist:
            log  = item.get("log", [])
            rep  = item.get("repeticao", "Sem repetição")
            ativa = item.get("concluida_em") is None  # ainda pendente ou reaberta

            card = tk.Frame(self.frame_hist_lista, bg=BG2, bd=0, pady=6, padx=10,
                            highlightbackground=BORDA, highlightthickness=1)
            card.pack(fill=tk.X, pady=4)

            # Cabeçalho do card: título + badge repetição + botão reabrir
            topo = tk.Frame(card, bg=BG2)
            topo.pack(fill=tk.X)
            badge_cor = {"Sem repetição": None, "Diariamente": COR_DIARIO,
                         "Semanalmente": COR_SEMANAL}[rep]
            if badge_cor:
                tk.Label(topo, text=f" 🔁 {rep} ", font=("Segoe UI", 7),
                         bg=badge_cor, fg="white").pack(side=tk.RIGHT, padx=(4, 0))
            if ativa:
                tk.Label(topo, text=" pendente ", font=("Segoe UI", 7),
                         bg=ACCENT2, fg="white").pack(side=tk.RIGHT, padx=(4, 0))
            else:
                tk.Button(topo, text="↩ Reabrir", font=("Segoe UI", 8),
                          bg=BG, fg=ACCENT, relief=tk.FLAT, cursor="hand2",
                          activebackground=BORDA, activeforeground=FG, padx=6, pady=0,
                          command=lambda i=item: self._reabrir_tarefa(i)).pack(side=tk.RIGHT)

            tk.Label(topo, text=item["texto"], font=("Segoe UI", 11, "bold"),
                     bg=BG2, fg=FG, anchor="w", wraplength=340).pack(
                     side=tk.LEFT, fill=tk.X, expand=True)

            # Separador
            tk.Frame(card, height=1, bg=BORDA).pack(fill=tk.X, pady=(4, 2))

            # Log de eventos
            if not log:
                # Compatibilidade com registros antigos sem log
                criado = item.get("criado_em", "")
                concluido = item.get("concluida_em", "")
                if criado:
                    log = [{"evento": "Criada", "quando": criado}]
                if concluido:
                    log.append({"evento": "Concluída", "quando": concluido})

            for entrada in log:
                icone, cor = ICONES.get(entrada["evento"], ("•", FG2))
                linha_log = tk.Frame(card, bg=BG2)
                linha_log.pack(fill=tk.X, pady=1)
                tk.Label(linha_log, text=icone, font=("Segoe UI", 9),
                         bg=BG2, fg=cor, width=2).pack(side=tk.LEFT)
                tk.Label(linha_log, text=entrada["evento"],
                         font=("Segoe UI", 9, "bold"), bg=BG2, fg=cor,
                         width=10, anchor="w").pack(side=tk.LEFT)
                tk.Label(linha_log, text=entrada["quando"],
                         font=("Segoe UI", 9), bg=BG2, fg=FG2,
                         anchor="w").pack(side=tk.LEFT)

    def _reabrir_tarefa(self, item):
        agora = datetime.now().strftime("%d/%m/%Y %H:%M")
        log_atualizado = list(item.get("log", []))
        log_atualizado.append({"evento": "Reaberta", "quando": agora})
        # Atualiza log no histórico (mantém a entrada)
        for h in self.historico:
            if h.get("criado_em") == item.get("criado_em") and h["texto"] == item["texto"]:
                h["log"] = log_atualizado
                h["concluida_em"] = None
                break
        self.tarefas.append({
            "texto": item["texto"],
            "concluida": False,
            "concluida_em": None,
            "criado_em": item.get("criado_em", agora),
            "repeticao": item.get("repeticao", "Sem repetição"),
            "log": log_atualizado
        })
        salvar_dados(self.tarefas, self.historico)
        self._atualizar_lista()
        self._atualizar_historico()

    # ─── Notificação ──────────────────────────────────────────────────────────

    def _iniciar_thread_notificacao(self):
        self._tick_contador()
        threading.Thread(target=self._loop_notificacao, daemon=True).start()

    def _tick_contador(self):
        if not self.notificacao_ativa:
            return
        self._atualizar_contador_label()
        self.root.after(1000, self._tick_contador)

    def _atualizar_contador_label(self):
        if self._pendentes() == 0 or not self.notificacoes_ligadas:
            self.label_prox.config(text="")
        else:
            restante = max(0, int(self.tempo_prox_notificacao - time.time()))
            m, s = divmod(restante, 60)
            self.label_prox.config(text=f"⏰ Próximo aviso: {m:02d}:{s:02d}")

    def _loop_notificacao(self):
        while self.notificacao_ativa:
            time.sleep(1)
            if not self.notificacoes_ligadas:
                continue
            if time.time() >= self.tempo_prox_notificacao:
                self.tempo_prox_notificacao = time.time() + self.intervalo_minutos * 60
                pendentes = self._pendentes()
                if pendentes > 0:
                    mais_antiga = next((t["texto"] for t in self.tarefas if not t["concluida"]), None)
                    self.root.after(0, self._mostrar_popup, pendentes, mais_antiga)

    def _mostrar_popup(self, pendentes, mais_antiga=None):
        if self._popup_aberto:
            return
        self._popup_aberto = True

        popup = tk.Toplevel()
        popup.title("")
        popup.overrideredirect(True)
        popup.attributes("-topmost", True)

        largura, altura = 320, 125
        sw = popup.winfo_screenwidth()
        sh = popup.winfo_screenheight()
        popup.geometry(f"{largura}x{altura}+{sw - largura - 16}+{sh - altura - 52}")
        popup.configure(bg=BG)

        borda = tk.Frame(popup, bg=ACCENT, padx=1, pady=1)
        borda.pack(fill=tk.BOTH, expand=True)
        frame = tk.Frame(borda, bg=BG, padx=14, pady=10)
        frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(frame, text="⏰  Lembrete de Tarefas", font=("Segoe UI", 11, "bold"),
                 bg=BG, fg=FG, anchor="w").pack(fill=tk.X)
        tk.Label(frame, text=f"Você tem {pendentes} tarefa(s) pendente(s)!",
                 font=("Segoe UI", 10), bg=BG, fg=FG2, anchor="w").pack(fill=tk.X, pady=(4, 0))

        if mais_antiga:
            txt = (mais_antiga[:38] + "…") if len(mais_antiga) > 38 else mais_antiga
            tk.Label(frame, text=f"📌 {txt}", font=("Segoe UI", 9, "italic"),
                     bg=BG, fg=FG_WARN, anchor="w").pack(fill=tk.X, pady=(2, 8))

        tk.Button(frame, text="OK", font=("Segoe UI", 9, "bold"),
                  bg=ACCENT, fg="white", relief=tk.FLAT, padx=16, pady=3, cursor="hand2",
                  activebackground="#6a5ae0", activeforeground="white",
                  command=lambda: self._fechar_popup(popup)).pack(side=tk.RIGHT)

    def _fechar_popup(self, popup):
        try:
            popup.destroy()
        except Exception:
            pass
        self._popup_aberto = False

    def _toggle_notificacoes(self):
        self.notificacoes_ligadas = not self.notificacoes_ligadas
        if self.notificacoes_ligadas:
            self.btn_notif_toggle.config(text="● Ligadas", bg=FG_OK)
            self.tempo_prox_notificacao = time.time() + self.intervalo_minutos * 60
        else:
            self.btn_notif_toggle.config(text="○ Desligadas", bg=ACCENT2)
        self._salvar_config()
        self._atualizar_contador_label()

    def _aplicar_intervalo(self):
        val = self.var_intervalo.get().strip()
        minutos = int(val) if val.isdigit() and int(val) > 0 else 30
        self.intervalo_minutos = minutos
        self.var_intervalo.set(str(minutos))
        self.tempo_prox_notificacao = time.time() + minutos * 60
        self._salvar_config()
        self._atualizar_contador_label()

    def _salvar_config(self):
        config = {"notificacoes_ligadas": self.notificacoes_ligadas,
                  "intervalo_minutos": self.intervalo_minutos}
        salvar_dados(self.tarefas, self.historico, config)

    def _ao_fechar(self):
        self.notificacao_ativa = False
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = AppTarefas(root)
    root.mainloop()
