# Simulador Walking Beam

Evolução incremental do estudo geométrico existente. Mantém coordenadas, controles,
salvar/abrir parâmetros e exportação A3 PDF/SVG/PNG. A nova aba **Sustentação
Termomecânica** resolve peso próprio e contatos unilaterais com alturas diferentes.

## Executar no Windows

Instale Python 3.12 com Tcl/Tk (distribuição oficial do Python). No PowerShell,
a partir desta pasta:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe simulador_wb.py
```

Para executar somente a interface geométrica anterior:

```powershell
.\.venv\Scripts\python.exe simulador_wb.py --geometrico
```

O arquivo original `simulador_wb` continua sendo Python executável. No Linux,
Tkinter e um display X são necessários para a interface; os testes estruturais
rodam sem display. Não é aplicativo web.

## Caso de parada de 2–3 h

A aba começa com móvel **20 mm abaixo** da fixa. Espessuras 200/225/250 mm e
largura 750–1950 mm foram fornecidas pelo usuário. Comprimento, temperaturas,
Steel Grade e propriedades precisam ser conferidos para a placa real.

Sem E(T), densidade e fonte, o aplicativo executa **somente geometria**. Não há
valores padrão de aço. É possível informar um E em GPa válido apenas na temperatura
média indicada, ou carregar um JSON com uma tabela. Classe baixo/médio carbono não
identifica uma curva de propriedades. Sem constitutiva calibrada e acoplamento de
fluência, a flecha elástica não permite concluir como a placa estará após 2–3 h.

As referências da Família 13 são apresentadas separadamente:

| Cenário | Referência em 4500 mm | Referência em 4860 mm |
|---|---:|---:|
| JSON original | 591 mm | 340 mm |
| Interface anterior | 720 mm | 490 mm |
| Proposta solicitada | 790 mm | 520 mm |

A tolerância triangular e `mid=4679,5 mm` permanecem como no projeto existente.
A lógica real MIN/MAX do PLC **não foi fornecida nem certificada**. A proposta
não é automaticamente segura. A placa espelhada é uma hipótese selecionável.

## Materiais e histórico

Consulte [formato dos dados](docs/DADOS.md). E é interpolado linearmente apenas
entre temperaturas fornecidas. Não há extrapolação. A temperatura superficial é
registrada, mas não substitui um perfil pela espessura: curvatura térmica não é
resolvida. Dilatação longitudinal é opcional e requer alpha(T); conserva massa,
com largura/espessura mantidas e origem da placa fixada em x (hipótese declarada).

A varredura calcula reações, CG e overhang em cada posição; mostra amostras
geométricas admissíveis e, se houver critérios de engenharia informados, amostras
que passam nas condições elásticas. Não interpola fronteiras nem fornece limite
operacional validado. Retomada: equilíbrios quase-estáticos entre móvel 20 mm
abaixo e 20 mm acima, sem impacto, velocidade ou histerese. As três seções são
avaliadas independentemente; falta geometria longitudinal para calcular colisões
nas transições.

Exportação da nova aba: relatório JSON, texto de interpretação e gráfico PNG.
O JSON contém casos, entradas materiais, discretização de contato, folgas e
reações por ponto/pad. Salve resultados fora dos arquivos de código.

## Validação

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe tests/gui_smoke.py
```

O segundo comando exige display e exercita a interface, salvar/abrir JSON,
exportações originais e a nova análise. As propriedades numéricas dos testes são
**fixtures sintéticas de verificação**, não fichas de Steel Grades.

Consulte [auditoria](docs/AUDITORIA.md), [equações e limitações](docs/MODELO.md) e
[relatório de testes](docs/RELATORIO_TESTES.md). O manual enviado pelo usuário é
referenciado na documentação; não foi incorporado como código ou como fonte de
E(T)/fluência que ele não fornece.
