# Relatório de validação

Executado em 10/10/2026, Linux Debian 13, Python 3.12.14, NumPy 2.5.3,
SciPy 1.18.1, Matplotlib 3.11.2, Tk 9.0, display Xvfb local. A inicialização e
os testes GUI passaram neste ambiente. **Windows não foi executado**; o lançador
e instruções usam Python/Tk portáveis e os caminhos são resolvidos pelo arquivo.
É necessária uma execução no Windows alvo antes de afirmar compatibilidade
operacional nessa máquina.

## Resultados

`python -m unittest discover -s tests -v`: **22 testes, todos passaram**.
Os testes incluem subcasos de comprimentos 4500/4560/4780/4860 mm, espessuras
200/225/250 mm, temperaturas de fixture 20/1000 °C e seções 1/2/3, além dos
três alinhamentos MIN/REF/MAX com deriva −150/0/+150 mm.

| Verificação | Resultado |
|---|---|
| Forças e momentos globais | Passou; erros relativos abaixo de 1e−5 |
| Reações ≥0, gaps ≥0, complementaridade | Passou nos casos verificados |
| Viga simplesmente apoiada, carga uniforme | Flecha/reações concordam com solução analítica; erro da tensão FE <0,1% |
| Móvel 20 mm abaixo | No fixture padrão, nenhuma carga nas móveis; gap não impõe flecha de 20 mm |
| Parada 2/3 h, mesma temperatura | Soluções elásticas idênticas; sem conclusão sobre fluência |
| Elevação de +20 a −20 mm de gap | Contato recuperado e carga transferida às móveis |
| Perda de pad fixo | Pad perdido sem reação; redistribuição respeita equilíbrio |
| Pad fora da placa | Sem reação |
| Apoio insuficiente / CG externo | Rejeitado como instável/marginal |
| Um pad finito sustentando a placa | Alerta explícito de concentração, não aprovação |
| Variação de largura 750/1950 mm | Peso escala com largura; flecha de viga uniforme é consistente |
| Espessuras/temperaturas | Equilíbrio e respostas verificadas com fixtures |
| Malha 150→75 mm; pads 2→4 segmentos | Diferença de flecha <2% no caso de refinamento |
| Material/dimensões ausentes | Somente geometria; sem forças/flecha fictícias |
| E/alpha fora da tabela | Extrapolação rejeitada |
| Dados de fluência ausentes | Nenhuma lei padrão aplicada |
| Norton separado | Taxa/tempo/sinal/faixas/fonte verificados com parâmetros sintéticos |
| Coordenadas e JSON legados | Preservados |
| Exportação A3 PDF/SVG/PNG | Passou |

`python tests/gui_smoke.py`: **passou** com display virtual. Exercitou a interface
geométrica isolada e a interface ampliada, três famílias, cenário manual,
salvar/abrir parâmetros JSON, exportações PDF/SVG/PNG, carregamento de material,
cálculo assíncrono, 36 comparações, 21 posições de deriva, três seções e
exportação de relatório JSON/TXT/PNG. A nova aba não alterou os parâmetros
geométricos durante a análise.

Durante desenvolvimento os testes detectaram elementos quase nulos gerados pela
grade regular junto às bordas dos pads. Corrigiu-se a construção da malha,
preservando os pontos reais de contato. Também se corrigiu a entrega de resultados
do worker à GUI: uma fila é lida pelo thread Tk, sem chamar Tk de outro thread.
As verificações foram repetidas após as correções.

## O que estes testes não estabelecem

Fixtures materiais são **sintéticas**, exclusivamente para verificar equações e
software. Não representam aço baixo/médio carbono real. Não houve ensaio físico,
comparação com dados de planta, cálculo plástico ou integração estrutural de
fluência. Não houve avaliação de colisões longitudinais/dinâmicas. A fórmula
PLC MIN/MAX continua uma reconstrução não validada com PLC real.

**Conclusão do caso real:** indeterminada. As dimensões fornecidas estão
incorporadas, mas E(T), densidade rastreável, temperatura real/histórico,
resistência e propriedades de fluência não foram fornecidos. Os testes demonstram
funcionamento do modelo elástico e preservação da aplicação; não demonstram
segurança de uma placa aquecida parada 2–3 h nem da retomada industrial.
