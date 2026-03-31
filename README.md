# Lista de Tarefas com Notificacoes

Aplicativo desktop para gerenciamento de tarefas pessoais. Desenvolvido em Python com interface gráfica, tema escuro e sem necessidade de instalação de programas adicionais para o usuário final.

## Sumario

- [Funcionalidades](#funcionalidades)
- [Onde as tarefas ficam salvas](#onde-as-tarefas-ficam-salvas)
- [Requisitos do sistema](#requisitos-do-sistema)
- [Como usar](#como-usar)
- [Como gerar seu proprio executavel](#como-gerar-seu-proprio-executavel)
  - [O que voce vai precisar](#o-que-voce-vai-precisar)
  - [Passo 1 — Instale o PyInstaller](#passo-1--instale-o-pyinstaller)
  - [Passo 2 — Navegue ate a pasta do arquivo](#passo-2--navegue-ate-a-pasta-do-arquivo)
  - [Passo 3 — Gere o executavel](#passo-3--gere-o-executavel)
  - [Passo 4 — Onde encontrar o executavel gerado](#passo-4--onde-encontrar-o-executavel-gerado)
  - [Outros exemplos de comandos](#outros-exemplos-de-comandos)
  - [Observacoes importantes](#observacoes-importantes)

![Interface do aplicativo](https://raw.githubusercontent.com/thiagocastro1721/Lista_de_Tarefas_com_Notificacao/main/interface.png)

## Onde as tarefas ficam salvas

Todas as tarefas, configurações e histórico são salvos automaticamente em um arquivo chamado `tarefas_app.json`. O local exato depende de como o aplicativo está sendo executado:

**Rodando como executável (`.exe`):**
O arquivo `tarefas_app.json` é criado na mesma pasta onde o `lista_tarefas.exe` estiver localizado.

```
C:\Users\SeuNome\Documents\ListaDeTarefas\
├── lista_tarefas.exe
└── tarefas_app.json       ← criado automaticamente aqui
```

**Rodando pelo editor de código (`.py`):**
O arquivo `tarefas_app.json` é criado na mesma pasta onde o `lista_tarefas.py` estiver salvo.

```
C:\Users\SeuNome\Documents\ListaDeTarefas\
├── lista_tarefas.py
└── tarefas_app.json       ← criado automaticamente aqui
```

> **Atenção:** ao mover o executável para outro local, leve o arquivo `tarefas_app.json` junto. Caso contrário, o aplicativo iniciará sem nenhuma tarefa salva e um novo arquivo será criado no novo local.

---

## Funcionalidades

**Cadastro de tarefas**
Cada tarefa pode ser criada com um texto descritivo, nível de prioridade (Alta, Média ou Baixa) e configurações de repetição. As tarefas são ordenadas automaticamente por prioridade na lista.

**Prioridade visual**
Cada nível de prioridade é exibido com uma cor distinta: vermelho para Alta, amarelo para Média e verde para Baixa, facilitando a identificação rápida do que é mais urgente.

**Repetição automática**
Tarefas podem ser configuradas para se repetir diariamente ou semanalmente. Quando concluídas, elas voltam automaticamente como pendentes no próximo ciclo, sem necessidade de recriação manual.

**Notificacoes agendadas**
Ao criar uma tarefa, é possível definir uma data e hora específica para receber uma notificação. O aplicativo oferece um seletor de calendário com botões de atalho como +15 min, +30 min, +1 hora e Amanhã para facilitar o preenchimento.

**Notificacoes ciclicas**
Além das notificações agendadas, o aplicativo exibe lembretes periódicos com a tarefa de maior prioridade ainda pendente. O intervalo entre os lembretes pode ser configurado em minutos.

![Notificacao do aplicativo](https://raw.githubusercontent.com/thiagocastro1721/Lista_de_Tarefas_com_Notificacao/main/notificacao.png)

**Painel de opcoes**
Permite ligar ou desligar as notificações, ajustar o intervalo dos lembretes cíclicos e ativar ou desativar a exclusão automática de tarefas do histórico com mais de 30 dias.

**Historico de tarefas**
Registra as últimas ações de cada tarefa: criação, conclusão e reabertura. O histórico pode ser mantido por 30 dias com exclusão automática ao final desse período, ou indefinidamente caso essa opção esteja desativada nas configurações.

**Calendario**
Exibe um calendário mensal com marcações visuais nos dias que possuem tarefas criadas ou com lembretes agendados. Ao clicar em um dia, as tarefas correspondentes são exibidas abaixo do calendário com detalhes de prioridade e status.

**Pesquisa em tempo real**
A aba de pesquisa filtra tarefas conforme o texto é digitado, exibindo o log completo de cada resultado encontrado.

**Subtarefas**
Cada tarefa pode conter subtarefas individuais, que podem ser marcadas como concluídas de forma independente.

**Persistencia de dados**
Todas as tarefas, configurações e histórico são salvos automaticamente em um arquivo chamado `tarefas_app.json`, localizado na mesma pasta do executável ou do arquivo `lista_tarefas.py`, dependendo de como o aplicativo for executado.

## Requisitos do sistema

- Windows 10 ou superior (para notificações nativas)
- Python 3.8 ou superior

## Como usar

> **Pré-requisito:** para executar o aplicativo pelo VS Code ou pelo terminal, o Python precisa estar instalado no seu computador. Caso ainda não tenha, siga os passos abaixo antes de continuar.

### Instalando o Python

1. Acesse o site oficial: **https://www.python.org/downloads**
2. Clique em **Download Python** — o site detecta automaticamente o Windows e oferece a versão mais recente
3. Abra o instalador baixado
4. **Importante:** antes de clicar em "Install Now", marque a opção **"Add Python to PATH"** na parte inferior da janela. Sem essa opção marcada, o comando `python` não será reconhecido pelo terminal

![Add Python to PATH](https://www.python.org/static/community_data/python-logo-master-v3-TM.png)

5. Clique em **Install Now** e aguarde a instalação terminar
6. Ao final, clique em **Close**

Para verificar se a instalação foi concluída corretamente, abra o Prompt de Comando e execute:

```
python --version
```

Se aparecer algo como `Python 3.x.x`, o Python está instalado e pronto para uso.

---

### Pelo Visual Studio Code

1. Abra o VS Code e selecione **File → Open Folder** para abrir a pasta onde está o arquivo `lista_tarefas.py`
2. No painel lateral, clique sobre o arquivo `lista_tarefas.py` para abri-lo
3. Pressione `F5` ou clique no botão **Run** (▶) no canto superior direito do editor
4. O aplicativo será iniciado em uma nova janela

> **Requisito:** certifique-se de que o Python está instalado e configurado no VS Code. Caso o editor solicite, selecione o interpretador Python pelo atalho `Ctrl + Shift + P` → `Python: Select Interpreter`.

### Pelo Prompt de Comando (CMD) ou PowerShell

1. Abra o **Prompt de Comando** (`cmd`) ou o **PowerShell** — pressione `Win + R`, digite `cmd` e pressione Enter
2. Navegue até a pasta onde o arquivo `lista_tarefas.py` está salvo. Por exemplo:

```
cd C:\Users\SeuNome\Documents\ListaDeTarefas
```

3. Execute o aplicativo com o comando:

```
python lista_tarefas.py
```

O aplicativo será iniciado em uma nova janela.

### Pelo executavel (.exe)

Caso você já possua o arquivo `lista_tarefas.exe` gerado:

1. Navegue até a pasta onde o executável está salvo
2. Dê um duplo clique sobre o arquivo `lista_tarefas.exe`
3. O aplicativo será iniciado diretamente, sem necessidade de ter o Python instalado

> **Observação:** na primeira execução, o arquivo `tarefas_app.json` será criado automaticamente na mesma pasta do executável.

### Notificacoes nativas do Windows (opcional)

Para ativar notificações nativas do Windows, instale uma das bibliotecas abaixo. O aplicativo funciona normalmente sem elas, mas as notificações usarão apenas popups internos.

```
pip install winotify
```

ou

```
pip install win10toast
```

---

## Como gerar seu proprio executavel

Esta seção explica como transformar o arquivo `.py` em um `.exe` que pode ser executado em qualquer computador Windows, mesmo sem o Python instalado. O processo é simples e feito pelo terminal.

### O que voce vai precisar

- Python 3.8 ou superior instalado no seu computador
- Os arquivos `lista_tarefas.py` e `tarefas.ico`
- Conexão com a internet para instalar o PyInstaller (apenas uma vez)

### Passo 1 — Instale o PyInstaller

Abra o terminal (Prompt de Comando ou PowerShell) e execute:

```
pip install pyinstaller
```

Aguarde a instalação terminar. Você verá uma mensagem informando que foi concluída com sucesso.

### Passo 2 — Navegue ate a pasta do arquivo

No terminal, acesse a pasta onde os arquivos `lista_tarefas.py` e `tarefas.ico` estão salvos. Por exemplo, se eles estiverem na sua pasta Documentos:

```
cd C:\Users\SeuNome\Documents
```

Substitua `SeuNome` pelo nome do seu usuário no Windows.

### Passo 3 — Gere o executavel

Execute o comando abaixo no terminal:

```
python -m PyInstaller --onefile --windowed --icon=tarefas.ico lista_tarefas.py
```

Explicando cada parte do comando:

- `--onefile` — gera um único arquivo `.exe`, mais fácil de distribuir
- `--windowed` — impede que uma janela preta de terminal apareça junto com o aplicativo
- `--icon=tarefas.ico` — define o ícone do executável
- `lista_tarefas.py` — nome do arquivo que será compilado

O processo pode levar alguns minutos. Ao terminar, você verá a mensagem `Building EXE from EXE-00.toc completed successfully`.

### Passo 4 — Onde encontrar o executavel gerado

Após a compilação, o PyInstaller cria uma pasta chamada `dist` dentro da pasta onde você está. O arquivo executável estará lá:

```
dist\lista_tarefas.exe
```

Esse arquivo pode ser copiado para qualquer computador Windows e executado com um duplo clique, sem necessidade de instalar o Python ou qualquer outra dependência.

> **Importante:** o arquivo `tarefas_app.json` com os dados das tarefas é criado automaticamente na mesma pasta onde o `lista_tarefas.exe` estiver localizado. Mantenha o executável e o arquivo `.json` juntos caso queira preservar suas tarefas ao mover o aplicativo para outro local.

### Outros exemplos de comandos

**Com nome personalizado para o executavel:**

```
pyinstaller --onefile --windowed --icon=tarefas.ico --name="Lista de Tarefas" lista_tarefas.py
```

O arquivo gerado será chamado `Lista de Tarefas.exe`.

**Recompilando sem redigitar o comando:**

Após a primeira compilação, o PyInstaller salva as configurações em um arquivo chamado `lista_tarefas.spec`. Para recompilar usando as mesmas configurações, basta executar:

```
pyinstaller lista_tarefas.spec
```

### Observacoes importantes

**Tamanho do arquivo:** o executável gerado costuma ter entre 15 e 40 MB, mesmo para projetos pequenos. Isso acontece porque o PyInstaller inclui o interpretador Python dentro do arquivo. É um comportamento normal.

**Alerta de antivirus:** alguns antivírus podem exibir um aviso ao abrir o executável gerado. Isso é um falso positivo comum em arquivos criados com o PyInstaller, pois a ferramenta é amplamente usada e reconhecida por softwares de segurança. O arquivo não representa risco real se você mesmo o gerou a partir do código-fonte.

**Compatibilidade:** o executável gerado no Windows funciona apenas no Windows. Se você precisar de uma versão para macOS ou Linux, o processo é o mesmo, mas deve ser realizado em um computador com o sistema correspondente.

**Pasta build:** além da pasta `dist`, o PyInstaller também cria uma pasta `build` com arquivos temporários de compilação. Ela pode ser apagada com segurança após a geração do executável.
