# Lista de Tarefas com Notificacoes

Aplicativo desktop para gerenciamento de tarefas pessoais. Desenvolvido em Python com interface gráfica, tema escuro e sem necessidade de instalação de programas adicionais para o usuário final.

![Interface do aplicativo](https://raw.githubusercontent.com/thiagocastro1721/Lista_de_Tarefas_com_Notificacao/main/interface.png)

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
Permite ligar ou desligar as notificações e ajustar o intervalo dos lembretes cíclicos.

**Historico de tarefas**
Registra as últimas ações de cada tarefa: criação, conclusão e reabertura. O histórico é mantido por 30 dias e excluído automaticamente após esse período.

**Pesquisa em tempo real**
A aba de pesquisa filtra tarefas conforme o texto é digitado, exibindo o log completo de cada resultado encontrado.

**Subtarefas**
Cada tarefa pode conter subtarefas individuais, que podem ser marcadas como concluídas de forma independente.

**Persistencia de dados**
Todas as tarefas, configurações e histórico são salvos automaticamente em um arquivo na pasta do usuário (`tarefas_app.json`), sem necessidade de banco de dados.

## Requisitos do sistema

- Windows 10 ou superior (para notificações nativas)
- Python 3.8 ou superior

## Como usar

Para rodar o aplicativo, abra o terminal na pasta onde está o arquivo e execute:

```
python lista_tarefas.py
```

Para notificações nativas do Windows, instale uma das bibliotecas abaixo (opcional, o aplicativo funciona sem elas):

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
- O arquivo `lista_tarefas.py`
- Conexão com a internet para instalar o PyInstaller (apenas uma vez)

### Passo 1 — Instale o PyInstaller

Abra o terminal (Prompt de Comando ou PowerShell) e execute:

```
pip install pyinstaller
```

Aguarde a instalação terminar. Você verá uma mensagem informando que foi concluída com sucesso.

### Passo 2 — Navegue ate a pasta do arquivo

No terminal, acesse a pasta onde o arquivo `lista_tarefas.py` está salvo. Por exemplo, se ele estiver na sua pasta Documentos:

```
cd C:\Users\SeuNome\Documents
```

Substitua `SeuNome` pelo nome do seu usuário no Windows.

### Passo 3 — Gere o executavel

Execute o comando abaixo no terminal:

```
pyinstaller --onefile --windowed lista_tarefas.py
```

Explicando cada parte do comando:

- `--onefile` — gera um único arquivo `.exe`, mais fácil de distribuir
- `--windowed` — impede que uma janela preta de terminal apareça junto com o aplicativo
- `lista_tarefas.py` — nome do arquivo que será compilado

O processo pode levar alguns minutos. Ao terminar, você verá a mensagem `Building EXE from EXE-00.toc completed successfully`.

### Passo 4 — Onde encontrar o executavel gerado

Após a compilação, o PyInstaller cria uma pasta chamada `dist` dentro da pasta onde você está. O arquivo executável estará lá:

```
dist\lista_tarefas.exe
```

Esse arquivo pode ser copiado para qualquer computador Windows e executado com um duplo clique, sem necessidade de instalar o Python ou qualquer outra dependência.

### Outros exemplos de comandos

**Com nome personalizado para o executavel:**

```
pyinstaller --onefile --windowed --name="Lista de Tarefas" lista_tarefas.py
```

O arquivo gerado será chamado `Lista de Tarefas.exe`.

**Com icone personalizado:**

Se você tiver um arquivo de ícone no formato `.ico`, pode incluí-lo assim:

```
pyinstaller --onefile --windowed --icon=icone.ico lista_tarefas.py
```

Substitua `icone.ico` pelo caminho completo do seu arquivo de ícone.

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
