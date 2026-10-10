# Auditoria e arquitetura proposta

O projeto original tem dois arquivos: `simulador_wb` (Python sem extensão) e
`familias_base.json`. Matplotlib e Tkinter compõem a interface. Não há testes,
modelo térmico, equilíbrio estrutural ou propriedades materiais.

As coordenadas FIXED/MOVING/ARMS, largura de 12170 mm e desenho A3 serão mantidos.
`support()` mede apenas contato geométrico e margem do CG. Não calcula forças.
Família 13: JSON p=591/q=340; interface sobrescreve p=720/q=490; proposta solicitada
p=790/q=520. Os três cenários serão identificados separadamente. `alignment()`
reconstrói tolerâncias por interpolação e envelope triangular, com mid=4679,5 mm.
A lógica real do PLC não foi fornecida: manter a fórmula existente não prova
que ela corresponde a clamps/modos reais. Essa diferença deve aparecer na UI.

Arquitetura incremental:
- `simulador_wb`: mantém o desenho e controles, acrescenta aba opcional.
- `simulador_wb.py`: lançador compatível com Windows e opção `--geometrico`.
- `wb_physics/materials.py`: propriedades declaradas com origem e interpolação
  apenas no intervalo de dados, sem bibliotecas fictícias de Steel Grades.
- `wb_physics/beam.py`: elementos Hermite Euler–Bernoulli, peso próprio,
  contato unilateral, alturas diferentes, reações e flecha.
- `wb_physics/analysis.py`: alinhamentos, seções, deriva, elevação e histórico.
- `wb_physics/creep.py`: Norton com parâmetros explícitos e rastreáveis;
  avaliação constitutiva separada, sem alegar evolução estrutural acoplada.
- `wb_physics/ui.py`: entradas, gráficos e exportação de relatório.
- `tests`: equilíbrio, solução analítica, gaps, retomada, regressão e materiais.

Equações previstas (SI interno, deslocamento vertical positivo para baixo):
I=b h³/12; q=ρ b h g; Π=1/2 uᵀKu−fᵀu.
Em cada ponto de pad: Cu≤g, R≥0 e R(g−Cu)=0.
Equilíbrio: Ku+CᵀR=f, ΣR=mg, ΣRx=mg xCG.
Gaps positivos significam apoios mais baixos, e não deformação imposta.
A superfície finita de cada pad será discretizada em pontos; a distribuição de
pressão é aproximação rígida e deverá passar por refinamento de malha.

Dados ausentes: dimensões reais (largura/espessura), Steel Grade e E(T), densidade,
dilatação, temperatura superficial/média e histórico por seção, fluência,
compliance dos pads, lógica PLC, geometria longitudinal das transições,
trajetória/velocidade de retomada, limites de tensão/flecha e margens aprovadas.
Sem E e densidade rastreáveis: somente geometria. Sem fluência: flecha elástica
instantânea, sem previsão de deformação após 2–3 h. Sem validação industrial:
nenhum resultado será denominado limite operacional seguro.
