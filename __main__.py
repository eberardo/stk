import warnings
import os
import shutil
import logging
import argparse
from rdkit import RDLogger
from os.path import join, basename, abspath

from .molecular import Molecule, CACHE_SETTINGS
from .ga import GAPopulation, GAInput
from .convenience_tools import (tar_output,
                                errorhandler,
                                streamhandler,
                                archive_output,
                                kill_macromodel)
from .ga import plotting as plot

warnings.filterwarnings("ignore")
RDLogger.logger().setLevel(RDLogger.CRITICAL)


# Get the loggers.
rootlogger = logging.getLogger()
rootlogger.addHandler(errorhandler)
rootlogger.addHandler(streamhandler)

logger = logging.getLogger(__name__)


class GAProgress:
    """
    Deals with logging the GA's progress.

    Attributes
    ----------
    ga_tools : :class:`.GATools`
        The :class:`.GATools` object holding the GA run settings.

    first_mol_name : :class:`int`
        The name the first unnamed molecule produced by the GA should
        be assigned.

    start_gen : :class:`int`
        The starting generation number, will be non ``1`` if a run is
        restarted.

    progress : :class:`.GAPopulation`
        A population where each subpopulation is a generation of the
        GA.

    db_pop : :class:`.GAPopulation` or :class:`NoneType`
        A population which holds every molecule made by the GA.

    """

    def __init__(self, ga_tools):
        self.ga_tools = ga_tools

        if ga_tools.input.progress_load:
            # The version of the molecule loaded from databases may not
            # have the properties calculated that the version loaded
            # from the previous GA run may have. As a result, first
            # turn the cache of to load the GA produced version and
            # then update the cache.
            CACHE_SETTINGS['ON'] = False
            for m in GAPopulation.load(ga_tools.input.progress_load,
                                       Molecule.from_dict):
                m.update_cache()
            CACHE_SETTINGS['ON'] = True
            self.progress = GAPopulation.load(ga_tools.input.progress_load,
                                              Molecule.from_dict)
            self.progress.ga_tools = ga_tools
        else:
            self.progress = GAPopulation(ga_tools=ga_tools)

        # The +1 is added so that the first mol's name is 1 more than
        # the max in the previous GA.
        self.first_mol_name = max((int(mol.name)+1 for mol
                                   in self.progress if
                                   mol.name.isnumeric()),
                                  default=0)

        self.start_gen = (1 if len(self.progress.populations) == 0
                          else len(self.progress.populations))

        self.db_pop = GAPopulation(ga_tools=ga_tools)

    def db(self, mols):
        """
        Adds `mols` to :attr:`db_pop`.

        Only molecules not already present are added.

        Parameters
        ----------
        mols : :class:`.GAPopulation`
            A group of molecules made by the GA.

        Returns
        -------
        None : :class:`NoneType`

        """

        if self.ga_tools.input.database_dump:
            self.db_pop.add_members(mols)

    def dump(self):
        """
        Creates output files for the GA run.

        The following files are created:

            progress.log
                This file holds the progress of the GA in text form.
                Each generation is reprented by the names of the
                molecules and their key and fitness.

            progress.json
                A population dump file holding `progress`. Only made if
                :attr:`progress_dump` is ``True``.

            database.json
                A population dump file holding every molecule made by
                the GA. Only made if :attr:`db_pop` is not ``None``.

        """

        with open('progress.log', 'w') as logfile:
            for sp in self.progress.populations:
                for mem in sp:
                    logfile.write('{} {} {}\n'.format(mem.name,
                                                      str(mem.key),
                                                      mem.fitness))
                logfile.write('\n')

        if self.ga_tools.input.progress_dump:
            self.progress.dump('progress.json')
        if self.ga_tools.input.database_dump:
            self.db_pop.dump('database.json')

    def log_pop(self, logger, pop):
        """
        Writes `pop` to `logger` at level ``INFO``.

        Parameters
        ----------
        logger : :class:`Logger`
            The logger object recording the GA.

        pop : :class:`.GAPopulation`
            A population which is to be added to the log.

        Returns
        -------
        None : :class:`NoneType`

        """

        if not logger.isEnabledFor(logging.INFO):
            return

        s = 'Population log:\n'

        try:
            u = '-'*os.get_terminal_size().columns
        except OSError as ex:
            # When testing os.get_terminal_size() will fail because
            # stdout is not connceted to a terminal.
            u = '-'*100

        s += u
        s += '\n{:<10}\t{:<40}\t{}\n'.format('molecule',
                                             'fitness',
                                             'unscaled_fitness')
        s += u
        for mem in sorted(pop, reverse=True):
            uf = {n: str(v) for n, v in mem.unscaled_fitness.items()}
            memstring = ('\n{0.name:<10}\t'
                         '{0.fitness:<40}\t{1}').format(mem, uf)
            s += memstring + '\n' + u
        logger.info(s)

    def debug_dump(self, pop, dump_name):
        """
        Creates a population dump file.

        Dumping only occurs `pop.ga_tools.input.pop_dumps` is ``True``.

        Parameters
        ----------
        pop : :class:`.GAPopulation`
            The population to be dumped.

        dump_name : :class:`str`
            The name of the file to which the population should be
            dumped.

        Returns
        -------
        None : :class:`NoneType`

        """

        if pop.ga_tools.input.pop_dumps:
            pop.dump(join('..', 'pop_dumps', dump_name))


def ga_run(ga_input):
    """
    Runs the GA.

    """

    # 1. Set up the directory structure.

    launch_dir = os.getcwd()
    # Running MacroModel optimizations sometimes leaves applications
    # open.This closes them. If this is not done, directories may not
    # be possible to move.
    kill_macromodel()
    # Move any ``output`` dir in the cwd into ``old_output``.
    archive_output()
    os.mkdir('output')
    os.chdir('output')
    root_dir = os.getcwd()
    # If logging level is DEBUG or less, make population dumps as the
    # GA progresses and save images of selection counters.
    mcounter = ccounter = gcounter = ''
    if ga_input.counters:
        os.mkdir('counters')
        cstr = join(root_dir, 'counters', 'gen_{}_')
        mcounter = cstr + 'mutation_counter.png'
        ccounter = cstr + 'crossover_counter.png'
        gcounter = cstr + 'selection_counter.png'
    if ga_input.pop_dumps:
        os.mkdir('pop_dumps')

    # Copy the input script into the ``output`` folder.
    shutil.copyfile(ifile, basename(ifile))
    # Make the ``scratch`` directory which acts as the working
    # directory during the GA run.
    os.mkdir('scratch')
    os.chdir('scratch')
    open('errors.log', 'w').close()

    # 2. Initialize the population.

    progress = GAProgress(ga_input.ga_tools())

    logger.info('Generating initial population.')
    init_func = getattr(GAPopulation, ga_input.initer().name)
    if init_func.__name__ != 'load':
        pop = init_func(**ga_input.initer().params,
                        size=ga_input.pop_size,
                        ga_tools=ga_input.ga_tools())
    else:
        # The version of the molecule loaded from databases may not
        # have the properties calculated that the version loaded from
        # the previous GA run may have. As a result, first turn the
        # cache off to load the GA produced version and then update the
        # cache.
        CACHE_SETTINGS['ON'] = False
        for m in init_func(**ga_input.initer().params):
            m.update_cache()
        CACHE_SETTINGS['ON'] = True
        pop = init_func(**ga_input.initer().params)
        pop.ga_tools = ga_input.ga_tools()

    id_ = pop.assign_names_from(progress.first_mol_name)

    progress.debug_dump(pop, 'init_pop.json')

    logger.info('Optimizing the population.')
    pop.optimize(ga_input.opter(), ga_input.processes)

    logger.info('Calculating the fitness of population members.')
    pop.calculate_member_fitness(ga_input.processes)

    logger.info('Normalizing fitness values.')
    pop.normalize_fitness_values()

    progress.log_pop(logger, pop)

    logger.info('Recording progress.')
    progress.progress.add_subpopulation(pop)
    progress.db(pop)

    # 3. Run the GA.

    for x in range(progress.start_gen, ga_input.num_generations+1):
        # Check that the population has the correct size.
        assert len(pop) == ga_input.pop_size

        logger.info(f'Generation {x} of {ga_input.num_generations}.')

        logger.info('Starting crossovers.')
        offspring = pop.gen_offspring(ccounter.format(x))

        logger.info('Starting mutations.')
        mutants = pop.gen_mutants(mcounter.format(x))

        logger.debug('Population size is {}.'.format(len(pop)))

        logger.info('Adding offsping and mutants to population.')
        pop += offspring + mutants

        logger.debug('Population size is {}.'.format(len(pop)))

        logger.info('Removing duplicates, if any.')
        pop.remove_duplicates()

        logger.debug('Population size is {}.'.format(len(pop)))

        id_ = pop.assign_names_from(id_)
        progress.debug_dump(pop, f'gen_{x}_unselected.json')

        logger.info('Optimizing the population.')
        pop.optimize(ga_input.opter(), ga_input.processes)

        logger.info('Calculating the fitness of population members.')
        pop.calculate_member_fitness(ga_input.processes)

        logger.info('Normalizing fitness values.')
        pop.normalize_fitness_values()

        progress.log_pop(logger, pop)
        progress.db(pop)

        logger.info('Selecting members of the next generation.')
        pop = pop.gen_next_gen(ga_input.pop_size, gcounter.format(x))

        logger.info('Recording progress.')
        progress.progress.add_subpopulation(pop)
        progress.debug_dump(progress.progress, 'progress.json')
        progress.debug_dump(progress.db_pop, 'database.json')
        progress.debug_dump(pop, f'gen_{x}_selected.json')

        # Check if any user-defined exit criterion has been fulfilled.
        if pop.exit(progress.progress):
            break

    kill_macromodel()
    os.chdir(root_dir)
    os.rename('scratch/errors.log', 'errors.log')
    progress.progress.normalize_fitness_values()
    progress.dump()
    logger.info('Plotting EPP.')
    plot.fitness_epp(progress.progress, ga_input.plot_epp, 'epp.dmp')
    progress.progress.remove_members(
                    lambda x:
                    pop.ga_tools.fitness.name not in x.progress_params)
    plot.parameter_epp(progress.progress, ga_input.plot_epp, 'epp.dmp')

    shutil.rmtree('scratch')
    pop.write('final_pop', True)
    os.chdir(launch_dir)
    if ga_input.tar_output:
        logger.info('Compressing output.')
        tar_output()
    archive_output()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='python -m stk')

    parser.add_argument('input_file', type=str)
    parser.add_argument('-l', '--loops', type=int, default=1,
                        help='The number times the GA should be run.')

    args = parser.parse_args()

    ifile = abspath(args.input_file)
    ga_input = GAInput(ifile)
    rootlogger.setLevel(ga_input.logging_level)
    logger.info('Loading molecules from any provided databases.')
    dbs = []
    for db in ga_input.databases:
        dbs.append(GAPopulation.load(db, Molecule.from_dict))

    for x in range(args.loops):
        ga_run(ga_input)
