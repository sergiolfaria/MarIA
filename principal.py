import numpy as np
import random
import json
import matplotlib.pyplot as plt
import pickle
from pyboy import PyBoy
from pyboy.utils import WindowEvent
import time

class Ambiente:
    def __init__(self, nome_arquivo='mario.gb', modo_silencioso=True):
        tipo_janela = "headless" if modo_silencioso else "SDL2"
        self.pyboy = PyBoy(nome_arquivo, window=tipo_janela, debug=modo_silencioso)
        self.pyboy.set_emulation_speed(100)
        self.mario = self.pyboy.game_wrapper
        self.mario.start_game()

    def calcular_fitness(self):
        # Aumentar os pesos dos componentes do fitness
        return self.mario.score + 10 * self.mario.level_progress + 2 * self.mario.time_left

    
    def fim_de_jogo(self):
        return self.mario.lives_left == 1 or self.mario.score < 0

    def reset(self):
        self.mario.reset_game()
        self.pyboy.tick()
        return self.get_estado()

    def passo(self, indice_acao, duracao):
        if self.fim_de_jogo():
            print("Fim de jogo detectado")
            return None, 0, 0, "Fim de Jogo"
        # TODO: Pode mudar as ações, ainda pode usar down e up
        acoes = {
            0: WindowEvent.PRESS_ARROW_LEFT,
            1: WindowEvent.PRESS_ARROW_RIGHT,
            2: WindowEvent.PRESS_BUTTON_A
        }
        acoes_liberacao = {
            0: WindowEvent.RELEASE_ARROW_LEFT,
            1: WindowEvent.RELEASE_ARROW_RIGHT,
            2: WindowEvent.RELEASE_BUTTON_A
        }

        acao = acoes.get(indice_acao, WindowEvent.PASS)
        self.pyboy.send_input(acao)
        for _ in range(duracao):
            self.pyboy.tick()

        acao_liberacao = acoes_liberacao.get(indice_acao, WindowEvent.PASS)
        self.pyboy.send_input(acao_liberacao)
        self.pyboy.tick()

        tempo_restante = self.mario.time_left
        progresso_nivel = self.mario.level_progress
        return self.get_estado(), self.calcular_fitness(), tempo_restante, progresso_nivel

    def get_estado(self):
        return np.asarray(self.mario.game_area())

    def fechar(self):
        self.pyboy.stop()

class Individuo:
    def __init__(self):
        self.acoes = [(acao := self.acao_ponderada(), self.duracao_ponderada() if acao == 2 else random.randint(1, 10)) for _ in range(5000)]
        self.fitness = 0


    def acao_ponderada(self):
        acoes_ponderadas = [0, 1, 2]
        pesos_acoes = [3, 5, 2] 
        return random.choices(acoes_ponderadas, weights=pesos_acoes, k=1)[0]

    def duracao_ponderada(self):
        duracoes_ponderadas = [6, 7, 8, 9, 10, 12, 20, 25,30]
        pesos_duracoes = [4, 1, 1, 1, 4, 4, 5, 5,9] 
        return random.choices(duracoes_ponderadas, weights=pesos_duracoes, k=1)[0]

    
    def avaliar(self, ambiente):
        estado = ambiente.reset()
        fitness_total = 0
        tempo_maximo = 0
        movimentos_direita = 0
        jogo_terminou = False

        for acao, duracao in self.acoes:
            if jogo_terminou == "Fim de Jogo":
                break
            novo_estado, fitness, tempo_restante, jogo_terminou = ambiente.passo(acao, duracao)
            fitness_total += fitness
            tempo_maximo = max(tempo_maximo, tempo_restante)
            movimentos_direita += 1 if acao == 1 else 0
            estado = novo_estado

        pontos_tempo = 500 if tempo_maximo > 0 else 0
        self.fitness = fitness_total + pontos_tempo + movimentos_direita * 5
        return self.fitness

# A divisão é para dar numeros mais manejáveis
def avaliar_fitness(individuo, ambiente):
    fitness = individuo.avaliar(ambiente)
    fitness_normalizado = fitness / 10000
    return fitness_normalizado

def iniciar_individuos(populacao):
    return [Individuo() for _ in range(populacao)]

def selecao(individuos, k=5, prob=0.75):
    selecionados = []
    for _ in range(len(individuos)):
        competidores = random.choices(individuos, k=k, weights=[individuo.fitness for individuo in individuos])
        vencedor = max(competidores, key=lambda individuo: individuo.fitness) if random.random() < prob else random.choice(competidores)
        selecionados.append(vencedor)
    return selecionados

def cruzamento(pai1, pai2):
    ponto_cruzamento1 = random.randint(1, len(pai1.acoes) - 1)
    ponto_cruzamento2 = random.randint(1, len(pai1.acoes) - 1)
    if ponto_cruzamento1 > ponto_cruzamento2:
        ponto_cruzamento1, ponto_cruzamento2 = ponto_cruzamento2, ponto_cruzamento1
    filho1 = Individuo()
    filho2 = Individuo()
    filho1.acoes = pai1.acoes[:ponto_cruzamento1] + pai2.acoes[ponto_cruzamento1:ponto_cruzamento2] + pai1.acoes[ponto_cruzamento2:]
    filho2.acoes = pai2.acoes[:ponto_cruzamento1] + pai1.acoes[ponto_cruzamento1:ponto_cruzamento2] + pai2.acoes[ponto_cruzamento2:]
    return filho1, filho2

def mutacao(individuo, taxa_mutacao=0.5):
    for i in range(len(individuo.acoes)):
        if random.random() < taxa_mutacao:  
            individuo.acoes[i] = (random.randint(0, 2), random.randint(1, 10))


def imprimir_acoes_individuo(individuo):
    nomes_acoes = ["esquerda", "direita", "A"]
    acoes = [f"{nomes_acoes[acao]} por {duracao} ticks" for acao, duracao in individuo.acoes]
    return acoes

def algoritmo_genetico(populacao, ambiente, geracoes=100):
    melhor_individuo = None
    melhor_fitness = -np.inf

    for geracao in range(geracoes):
        for individuo in populacao:
            individuo.fitness = avaliar_fitness(individuo, ambiente)
            print(f"Fitness: {individuo.fitness}")

        selecionadas = selecao(populacao)
        descendentes = []
        while len(descendentes) < len(populacao) - len(selecionadas):
            pai1, pai2 = random.sample(selecionadas, 2)
            filho1, filho2 = cruzamento(pai1, pai2)
            descendentes.extend([filho1, filho2])

        for filho in descendentes:
            mutacao(filho)

        populacao = selecionadas + descendentes

        fitness_atual = max(individuo.fitness for individuo in populacao)
        individuo_atual = max(populacao, key=lambda n: n.fitness)
        if fitness_atual > melhor_fitness:
            melhor_fitness = fitness_atual
            melhor_individuo = individuo_atual

        print(f"Geração {geracao}: Melhor Fitness {melhor_fitness}")
        print(f"Melhores Ações: {imprimir_acoes_individuo(melhor_individuo)}")

    return melhor_individuo

def rodar_melhor_modelo(ambiente, melhor_individuo):
    while True:
        estado = ambiente.reset()
        for acao in melhor_individuo.acoes:
            estado, fitness, tempo_restante, progresso_nivel = ambiente.passo(acao)

        print("Loop completado, reiniciando...")

ambiente = Ambiente(modo_silencioso=False)
populacao = iniciar_individuos(10)
algoritmo_genetico(populacao, ambiente)

# TODO: O que fazer com tamanho dos indivíduos? Podem aumentar ao longo do tempo?