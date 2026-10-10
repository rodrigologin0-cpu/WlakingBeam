# Formato de material e histórico

A UI aceita JSON UTF-8 com `material` e opcionalmente históricos. Modelo de
estrutura abaixo: os `null` são campos a preencher com dados reais, não valores
válidos. A interface rejeita o modelo enquanto não forem preenchidos.

```json
{
  "material": {
    "grade": "INFORMAR GRAU/ESPECIFICAÇÃO",
    "source": "INFORMAR FICHA/ENSAIO, VERSÃO E CONDIÇÕES",
    "density_kg_m3": null,
    "elastic_table": [[null, null], [null, null]],
    "expansion_table": [[null, null], [null, null]]
  },
  "thermal_history_by_section": {
    "1": [{"hours": 0, "mean_c": null, "surface_c": null},
          {"hours": 2, "mean_c": null, "surface_c": null},
          {"hours": 3, "mean_c": null, "surface_c": null}]
  }
}
```

`elastic_table`: `[temperatura °C, E Pa]`, não GPa. Pelo menos um ponto; ordenação
estrita, temperaturas únicas, valores finitos e E>0. Um único ponto só autoriza
exatamente aquela temperatura. `expansion_table` pode ser omitida/vazia quando
não houver dilatação; `[temperatura °C, alpha 1/K]`. Históricos nas chaves `1`,
`2`, `3`: tempo em horas ordenado, temperatura média obrigatória e superficial
opcional. Cada seção usa seu próprio histórico; não se inventa um histórico
para outra seção. Na ausência de histórico, a UI mostra 0/2/3 h com T constante,
identificando a natureza elástica da curva.

Opcional `creep` (substitua todos os null por parâmetros calibrados):

```json
{
  "grade": "MESMO GRAU DO MATERIAL",
  "source": "FONTE E UNIDADES DA CALIBRAÇÃO NORTON",
  "A_pa_n_s": null,
  "n": null,
  "Q_j_mol": null,
  "temperature_range_c": [null, null],
  "stress_range_pa": [null, null]
}
```

A unidade de A depende de n. Não usar parâmetros de MPa numa implementação que
recebe Pa sem conversão. São necessários limites de calibração. O programa
**não** converte a deformação de fluência em flecha nem prediz contato progressivo;
a avaliação constitutiva é separada e em tensão constante.

Dados ainda necessários para concluir o caso industrial: Steel Grade específico,
E(T), densidade/fonte, resistência em temperatura, ensaios e lei de fluência,
históricos reais por seção, pad compliance, espessura efetiva em temperatura,
perfil térmico, lógica PLC, tolerâncias combinadas e geometria/velocidade das
transições. Espessuras 200/225/250 mm e largura 750–1950 mm já foram informadas.
