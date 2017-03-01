"""
Tests for normalization functions.

"""

from os.path import join
from ..ga import Normalization
from .test_population import generate_population

population = generate_population()

def test_combine():

    # Each member will have a fitness value of form:
    #   [1,1,1,1] or [2,2,2,2]
    # Where the number represnts the index in the population.
    # After combination, the fitness value should be 4*rank.
    for i, mem in enumerate(population, 1):
        mem.fitness = [i for _ in range(4)]

    Normalization.combine(None, population, [1,1,1,1], [1,1,1,1])

    for i, mem in enumerate(population, 1):
        assert mem.fitness == i*4

def test_magnitudes():

    for mem in population:
        mem.fitness = [1, 10, 100, -100]

    Normalization.magnitudes(None, population)

    for mem in population:
        assert all(x == 1 for x in mem.fitness)

def test_shift_elements():

    for i, mem in enumerate(population):
        mem.fitness = [i, 10*i, -i, -1000*i]

    Normalization.shift_elements(None, population, indices=[2, 3])

    for mem in population:
        assert mem.fitness[2] > 0
        assert mem.fitness[3] > 0

def test_invert():

    for i, mem in enumerate(population, 1):
        mem.fitness = i

    Normalization.invert(None, population)

    for i, mem in enumerate(population, 1):
        assert mem.fitness == 1/i
