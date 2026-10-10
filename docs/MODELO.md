# Modelo físico e limites de interpretação

## Viga Euler–Bernoulli e contato unilateral

A placa é representada por uma viga na direção do comprimento transversal do
forno. A largura b integra o peso e a rigidez; não há distribuição longitudinal
2D/3D. Dimensões internas em metros, E em Pa, densidade em kg/m³; entradas da UI
em mm e GPa. Peso uniforme `q=ρ b h g`, `I=b h³/12`, `g=9,80665 m/s²`.

Elementos Hermite cúbicos com graus de liberdade `(w, θ)` por nó:

```
          [ 12    6ℓ   -12    6ℓ ]
Ke=EI/ℓ³ [ 6ℓ   4ℓ²  -6ℓ   2ℓ²]
          [-12   -6ℓ    12   -6ℓ ]
          [ 6ℓ   2ℓ²  -6ℓ   4ℓ²]
fe=q [ℓ/2, ℓ²/12, ℓ/2, -ℓ²/12]ᵀ
```

Deslocamento w positivo para baixo. Em cada ponto de pad rígido, `w ≤ gap`;
20 mm de gap significa apoio 20 mm abaixo, não deslocamento prescrito. A solução
minimiza `Π=1/2 uᵀKu−fᵀu` com restrições de contato. Condições KKT:

```
Ku + CᵀR = f
R ≥ 0 ; gap−Cu ≥ 0 ; R (gap−Cu) = 0
```

Um conjunto ativo primal remove apoios que precisariam tracionar, acrescenta
contatos violados e resolve equilíbrio. Há condensação estática das rotações e
graus de liberdade fora dos contatos. A implementação normaliza posições por L
e deslocamentos por `qL⁴/(EI)` para reduzir diferenças de escala.

Cada pad finito possui bordas e centro (2 segmentos por padrão). O conjunto de
restrições aproxima uma superfície rígida: não é uma distribuição de pressão
calibrada nem um modelo da deformação do pad. O domínio de contato é truncado
pela extremidade da placa; pads fora dela ou desativados têm reação zero.
A soma das reações nos pontos fornece a reação do pad; nenhum peso é distribuído
por proximidade ou igualmente. `width_m=0` no solver é um apoio pontual ideal,
usado no teste analítico; a interface exige largura de pad positiva.

Malha auxiliar com elementos de até aproximadamente 150 mm, incluindo bordas e
centros dos pads. Pontos regulares muito próximos dos contatos são removidos
para evitar elementos quase nulos. O teste de refinamento usa 75 mm e quatro
segmentos por pad. Refinamento é necessário para aplicações além dos casos
verificados, especialmente contatos muito curtos.

Reações verificadas por `ΣR=mg` e `ΣRx=mg L/2`; resíduo acima de 1e−5 relativo
recusa o resultado. Sem dois pontos distintos de contato ou com CG fora do
envelope de candidatos, não se apresenta solução estável. Concentrar carga em
um pad finito pode ser matematicamente possível: recebe alerta, não aprovação.
A deformada é interpolada por funções Hermite, e a tensão elástica máxima é
estimada por `σ=E h |w''|/2`; não inclui concentração local/plasticidade.

## Temperatura, tempo e dilatação

E(T) é fornecido pelo usuário e interpolado linearmente sem extrapolação.
A fonte é registrada, mas sua confiabilidade industrial não é certificada pelo
programa. Temperatura média uniforme é uma aproximação; temperaturas superficial
e inicial são registradas. Sem um perfil pela espessura não há curvatura térmica.

Dilatação opcional: `εth=∫alpha(T)dT`, `Lhot=Lcold(1+εth)`. Extremo esquerdo
fixado na coordenada x, sem restrição axial/atrito. Largura e espessura permanecem
nas informadas; densidade equivalente é ajustada para conservar a massa. Isso
não representa expansão isotrópica completa ou contato/fricção reais.

Históricos por seção são amostras de equilíbrios elásticos instantâneos. Uma
curva de flecha versus tempo sem alteração de T é constante **por hipótese**,
não evidencia ausência de fluência. Perda progressiva de contatos por deformação
permanente não é prevista por esses equilíbrios.

O módulo constitutivo separado `creep.py` implementa Norton–Arrhenius:
`εdot=A |σ|ⁿ exp[-Q/(R T)] sign(σ)`; R=8,314462618 J/(mol K).
A em Pa^(-n)/s; Q em J/mol; T em K. Requer grade, fonte, A,n,Q e faixas de
calibração de tensão/temperatura. A UI pode mostrar deformação constitutiva sob
**tensão constante**, mas não a converte em flecha. Não há integração da fluência
nos elementos nem redistribuição estrutural dependente do tempo. Só implementar
esse acoplamento quando houver modelo/ensaios calibrados; dados atuais não o
permitem. Não há parâmetros numéricos padrão de fluência.

## Retomada, transições e limites

Elevar a móvel altera gaps. Cada posição é um equilíbrio unilateral independente;
calcula contato recuperado e transferência estática de carga. Não simula impacto,
esmagamento, trajetória tridimensional, parede deformável ou movimento simultâneo
das três seções. O gap da móvel em relação à solução inicial ajuda a identificar
quando haverá contato, mas contato quase-estático não é previsão de colisão.

A coordenada x original é preservada. Folgas laterais usam as paredes existentes,
incluindo recuo de 35 mm na S3. As seções são avaliadas separadamente: faltam
coordenadas longitudinais, folgas, velocidades e trajetórias para avaliar riscos
de transição e retomada dinâmica.

Distinções na saída:
- **Geométrico:** amostras com placa entre paredes e CG interno ao envelope de
  pelo menos dois pads em cada grupo fixo/móvel; não exige apoio vertical.
- **Termomecânico elástico calculado:** somente amostras que satisfazem limites de
  flecha, tensão e margem do CG fornecidos; sem fluência/plasticidade/resistência
  certificada. Sem limites, resultado indeterminado. Não são intervalos contínuos
  comprovados entre amostras nem uma margem de engenharia automaticamente válida.
- **Operacional validado:** indisponível até validação industrial e dados completos.

Não prevê flambagem axial, cisalhamento, torsão, deformações de placa, dano,
plasticidade, gradientes térmicos, contato longitudinal ou creep acoplado. Alertas
para L/h<10, |w|/L>0,02 ou rotações>0,1 rad identificam limitações do regime linear;
não são limites de aprovação. No caso real, E(T), fluência e limites de resistência
continuam ausentes: não é possível concluir se a placa parada por 2–3 h estará
segura ao reiniciar.

## Referência documental recebida

*Manual de Diagnóstico de Processo — Reaquecimento de Placas*, seção 6.1,
página 18 do PDF recebido: mapa evita overhang excessivo, recomenda no mínimo
dois apoios e menciona erro de posição ±50 mm, erro de comprimento ±50 mm,
deslocamento ±100 mm e expressão genérica de dilatação 1,3×10⁻⁵ ΔT. Esses itens
são contexto de processo, não E(T), lei de fluência ou certificação dos cenários.
O coeficiente não foi aplicado automaticamente a um Steel Grade desconhecido.
O manual não fornece a lógica completa MIN/MAX do PLC exigida para validar a
reconstrução triangular do aplicativo.
