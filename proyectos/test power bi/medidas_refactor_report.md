# Informe refactorización de medidas

Generado desde el log de reemplazos. Se quitaron llamadas `FORMAT(...)` para producir medidas numéricas.

Se proponen los siguientes `formatString` para las expresiones refactorizadas:

## 1
- Format original: 0.0%
- Expresión (preview): `CALCULATE(SUM(prime_indicadores_mes_grupos[venta_neta]), prime_indicadores_mes_grupos[grupo]="PRIME"),"#,0" 			    ), 			 			    "2- %Part. Vta Prime/Wong", 			        VAR vtaPrime = CALCULATE(SUM(pri`

## 2
- Format original: 0.0%
- Expresión (preview): `CALCULATE(SUM(prime_indicadores_mes_grupos[trx]), prime_indicadores_mes_grupos[grupo]="PRIME"   ), 			            "#,0" 			        ), 			 			    "4- %Part. Trx Prime/Wong", 			        VAR trxPrime = C`

## 3
- Format original: 0.0%
- Expresión (preview): `CALCULATE(SUM(prime_indicadores_mes_grupos[clientes]), prime_indicadores_mes_grupos[grupo]="PRIME"   ), 			            "#,0" 			        ), 			 			    "6- %Part. Clientes Prime/Wong", 			        VAR cl`

## 4
- Format original: #,0
- Expresión (preview): `CALCULATE(AVERAGE(prime_indicadores_mes_grupos[gasto_prom]), prime_indicadores_mes_grupos[grupo]="PRIME")`

## 5
- Format original: #,0
- Expresión (preview): `CALCULATE( 			            AVERAGE(prime_indicadores_mes_grupos[frecuencia]), 			            prime_indicadores_mes_grupos[grupo] = "PRIME" 			        ), 			        "#,0.00" 			    ), 			 			    "9- Tic`

## 6
- Format original: 0.0%
- Expresión (preview): `DIVIDE(vtaPromo, vtaNetaTotal)`

## 7
- Format original: #,0
- Expresión (preview): `SUM(promocional_mes[clientes_promocional])`

## 8
- Format original: 0.0%
- Expresión (preview): `DIVIDE(cliPromo, cliTotal2)`

## 9
- Format original: #,0
- Expresión (preview): `SUM(promocional_mes[dsct_bruto_promocional])`

## 10
- Format original: 0.0%
- Expresión (preview): `CALCULATE( 			                SUM(prime_indicadores_semana_grupos[venta_neta]),  			                prime_indicadores_semana_grupos[grupo] = "PRIME" 			            ), 			            "#,0" 			        )`

## 11
- Format original: 0.0%
- Expresión (preview): `CALCULATE( 			                SUM(prime_indicadores_semana_grupos[trx]),  			                prime_indicadores_semana_grupos[grupo] = "PRIME" 			            ), 			            "#,0" 			        ), 			 	`

## 12
- Format original: 0.0%
- Expresión (preview): `CALCULATE( 			                SUM(prime_indicadores_semana_grupos[clientes]),  			                prime_indicadores_semana_grupos[grupo] = "PRIME" 			            ), 			            "#,0" 			        ), `

## 13
- Format original: #,0
- Expresión (preview): `CALCULATE( 			                AVERAGE(prime_indicadores_semana_grupos[gasto_prom]),  			                prime_indicadores_semana_grupos[grupo] = "PRIME" 			            ), 			            "#,0" 			     `

## 14
- Format original: 0.0%
- Expresión (preview): `DIVIDE(vtaPromo, vtaNetaTotal)`

## 15
- Format original: #,0
- Expresión (preview): `SUM(promocional_semana[clientes_promocional])`

## 16
- Format original: 0.0%
- Expresión (preview): `DIVIDE(cliPromo, cliTotal2)`

## 17
- Format original: #,0
- Expresión (preview): `SUM(promocional_semana[dsct_bruto_promocional])`

## 18
- Format original: 0.0%
- Expresión (preview): `CALCULATE( 			                SUM(prime_indicadores_mes_grupos[venta_neta]),  			                prime_indicadores_mes_grupos[grupo]="NO PRIME" 			            ),  			            "#,0" 			        ), 		`

## 19
- Format original: 0.0%
- Expresión (preview): `CALCULATE( 			                SUM(prime_indicadores_mes_grupos[trx]),  			                prime_indicadores_mes_grupos[grupo]="NO PRIME" 			            ), 			            "#,0" 			        ), 			 			   `

## 20
- Format original: 0.0%
- Expresión (preview): `CALCULATE( 			                SUM(prime_indicadores_mes_grupos[clientes]),  			                prime_indicadores_mes_grupos[grupo]="NO PRIME" 			            ), 			            "#,0" 			        ), 			 	`

## 21
- Format original: 0.0%
- Expresión (preview): `CALCULATE( 			                AVERAGE(prime_indicadores_mes_grupos[gasto_prom]),  			                prime_indicadores_mes_grupos[grupo]="NO PRIME" 			            ), 			            "#,0" 			        ),`

## 22
- Format original: 0.0%
- Expresión (preview): `CALCULATE( 			                SUM(prime_indicadores_semana_grupos[trx]),  			                prime_indicadores_semana_grupos[grupo] = "NO PRIME" 			            ),  			            "#,0" 			        ), 	`

## 23
- Format original: 0.0%
- Expresión (preview): `CALCULATE( 			                SUM(prime_indicadores_semana_grupos[clientes]),  			                prime_indicadores_semana_grupos[grupo] = "NO PRIME" 			            ), 			            "#,0" 			        `


