# TP1 - Engenharia de Software

**Nomes**:
  - Felipe Reis Campanha Ribeiro (back)
  - Gabriel Shimada de Oliveira (full)
  - Julia Freitas Fernandes Pires (full)

## Objetivo do Sistema

O sistema consiste em um aplicativo de turismo dedicado à cidade de Belo Horizonte. A idéia é que um administrador tenha acesso a um banco de dados em um servidor e que esse administrador possa registrar diversos pontos de interesse (PDI) e tours, que são coleções de PDIs. Os usuários serão turistas que terão uma versão do aplicativo em seus celulares que mostra um mapa da região com suas localizações e os PDIs de um tour escolhido. À medida que eles andam pela cidade e passam pelos PDIs, estes vão sendo mostrdos como já visitados. Um usuário que selecionou um tour pode também criar um grupo. Usuários podem entrar neste grupo via login e senha e poderão consultar as localizações uns dos outros, bem como os PDIs que visitaram. As localizações serão dadas via simulações e o aplicativo web mostrará um mapa da cidade com os usuários fazendo o percurso.

## Tecnologias

O servidor será uma aplicação em Python dockerizada e que contará com um banco de dados SQL para armazenar os PDIs, tours, logins e senhas.
O frontent será feito com Javascript e deverá mostrar os PDIs e localizações de cada pessoa no mapa.
A comunicação entre ambos será feita via RabbitMq ou REST (a decidir).

## Histórias de Usuário

