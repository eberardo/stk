import warnings
import os
import shutil
import logging
import argparse
from rdkit import RDLogger
from os.path import join, basename, abspath

from .ga import (Population,
                 GAInput, InputHelp)
from .convenience_tools import (tar_output,
                                archive_output, kill_macromodel)
from .ga import plotting as plot

warnings.filterwarnings("ignore")
RDLogger.logger().setLevel(RDLogger.CRITICAL)

# fhandler = logging.FileHandler(
#                     os.path.join(os.getcwd(), 'output/failures.txt'),
#                     delay=True)
# fhandler.setLevel = logging.ERROR

logger = logging.getLogger(__name__)
# logger.addHandler(fhandler)


class GAProgress:
    """
    Deals with logging the GA's progress.

    Attributes
    ----------
    progress_dump : bool
        If ``True`` a population dump file `progress.json` is made in
        the output directory. Each subpopulation of this population
        represents a generation of the GA.

    progress : Population
        A population where each subpopulation is a generation of the
        GA.

    db_pop : Population or None
        A population which holds every molecule made by the GA.

    """

    def __init__(self, progress_dump, db_dump, ga_tools):
        self.progress_dump = progress_dump
        self.progress = Population(ga_tools)
        self.db_pop = Population() if db_dump else None

    def db(self, mols):
        """
        Adds `mols` to `db_pop`.

        Only molecules not already present are added.

        Parameters
        ----------
        mols : Population
            A group of molecules made by the GA.

        Modifies
        --------
        db_pop : Population
            `mols` are added to this population.

        Returns
        -------
        None : NoneType

        """

        if self.db_pop is not None:
            self.db_pop.add_members(mols)

    def dump(self):
        """
        Creates output files for the GA run.

        Modifies
        --------
        progress.log
            This file holds the progress of the GA in text form. Each
            generation is reprented by the names of the molecules and
            their key and fitness.

        progress.json
            A population dump file holding `progress`. Only made if
            `progress_dump` is ``True``.

        database.json
            A population dump file holding every molecule made by the
            GA. Only made if `db` is not ``None``.

        """

        with open('progress.log', 'w') as logfile:
            for sp in self.progress.populations:
                for mem in sp:
                    logfile.write('{} {} {}\n'.format(mem.name,
                                                      str(mem.key),
                                                      mem.fitness))
                logfile.write('\n')

        if self.progress_dump:
            self.progress.dump('progress.json')
        if self.db_pop is not None:
            self.db_pop.dump('database.json')

    def log_pop(self, logger, pop):
        """
        Writes `pop` to `logger` at level INFO.

        Parameters
        ----------
        logger : Logger
            The logger object recording the GA.

        pop : Population
            A population which is to be added to the log.

        Returns
        -------
        None : NoneType

        """

        if not logger.isEnabledFor(logging.INFO):
            return

        s = 'Population log:\n'
        for mem in sorted(pop, reverse=True):
            uf = {n: str(v) for n, v in mem.unscaled_fitness.items()}
            s += ('\n{0.name} {0.fitness} {1}').format(mem, uf)
        logger.info(s)

    def debug_dump(self, pop, dump_name):
        """
        Creates a population dump file.

        The dump file is made only if logging level is DEBUG or below.

        Parameters
        ----------
        pop : Population
            The population to be dumped.

        dump_name : str
            The name of the file to which the population should be
            dumped.

        Modifies
        --------
        dump_path
            A population dump file is made at this location.

        Returns
        -------
        None : NoneType

        """

        if logging.getLogger(__name__).isEnabledFor(logging.DEBUG):
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
    if logger.isEnabledFor(logging.DEBUG):
        os.mkdir('counters')
        os.mkdir('pop_dumps')
        cstr = join(root_dir, 'counters', 'gen_{}_')
        mcounter = cstr + 'mutation_counter.png'
        ccounter = cstr + 'crossover_counter.png'
        gcounter = cstr + 'selection_counter.png'
    # Copy the input script into the ``output`` folder.
    shutil.copyfile(ifile, basename(ifile))
    # Make the ``scratch`` directory which acts as the working
    # directory during the GA run.
    os.mkdir('scratch')
    os.chdir('scratch')

    # 2. Initialize the population.

    progress = GAProgress(ga_input.progress_dump,
                          ga_input.database_dump,
                          ga_input.ga_tools())

    logger.info('Generating initial population.')
    init_func = getattr(Population, ga_input.initer().name)
    pop = init_func(**ga_input.initer().params,
                    size=ga_input.pop_size,
                    ga_tools=ga_input.ga_tools())
    id_ = pop.assign_names_from(0)

    progress.debug_dump(pop, 'init_pop.json')
    logger.info('Optimizing the population.')
    pop.optimize_population()
    logger.info('Calculating the fitness of population members.')
    pop.calculate_member_fitness()
    logger.info('Normalizing fitness values.')
    pop.normalize_fitness_values()
    progress.log_pop(logger, pop)
    logger.info('Recording progress.')
    progress.progress.add_subpopulation(pop)
    progress.db(pop)

    # 3. Run the GA.

    for x in range(1, ga_input.num_generations+1):
        # Check that the population has the correct size.
        assert len(pop) == ga_input.pop_size
        logger.info('Generation {} of {}.'.format(
                                x, ga_input.num_generations))
        logger.info('Starting crossovers.')
        offspring = pop.gen_offspring(ccounter.format(x))
        logger.info('Starting mutations.')
        mutants = pop.gen_mutants(mcounter.format(x))
        logger.info('Adding offsping and mutants to population.')
        pop += offspring + mutants
        logger.info('Removing duplicates, if any.')
        pop.remove_duplicates()
        id_ = pop.assign_names_from(id_)
        progress.debug_dump(pop, 'gen_{}_unselected.json'.format(x))
        logger.info('Optimizing the population.')
        pop.optimize_population()
        logger.info('Calculating the fitness of population members.')
        pop.calculate_member_fitness()
        logger.info('Normalizing fitness values.')
        pop.normalize_fitness_values()
        progress.log_pop(logger, pop)
        progress.db(pop)
        logger.info('Selecting members of the next generation.')
        pop = pop.gen_next_gen(ga_input.pop_size, gcounter.format(x))
        logger.info('Recording progress.')
        progress.progress.add_subpopulation(pop)
        progress.debug_dump(pop, 'gen_{}_selected.json'.format(x))
        # Check if any user-defined exit criterion has been fulfilled.
        if pop.exit():
            break

    kill_macromodel()
    os.chdir(root_dir)
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
    if logger.isEnabledFor(logging.DEBUG):
        logger.info('Compressing output.')
        tar_output()
    archive_output()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
     prog='python -m mmea',
     description=('MMEA in can be run in a number of ways.'
                  ' Each type of run can be invoked by one'
                  ' of the listed commands.'
                  ' For details on a command use: command -h.'))
    commands = parser.add_subparsers(help='commands')

    run = commands.add_parser('run', description='Runs the GA.')
    run.add_argument('INPUT_FILE', type=str)
    run.add_argument('-l', '--loops', type=int, default=1,
                     help='The number times the GA should be run.')

    helper = commands.add_parser(
             'helper',
             description=('Provides a description variables which'
                          ' need to be defined in an input file.'))
    helper.add_argument(
            'KEYWORD', type=str,
            choices=list(InputHelp.modules.keys()),
            help=('The name of a variable which needs to be defined'
                  ' in an input file.'))

    args = parser.parse_args()

    if 'INPUT_FILE' in dir(args):

        ifile = abspath(args.INPUT_FILE)
        ga_input = GAInput(ifile)

        f = '\n' + '='*os.get_terminal_size().columns + '\n\n'
        logging.basicConfig(level=ga_input.logging_level,
                            format=f+('%(asctime)s - %(levelname)s - '
                                      '%(name)s - %(message)s'),
                            datefmt='%H:%M:%S')

        logger.info('Loading molecules from any provided databases.')
        dbs = []
        for db in ga_input.databases:
            dbs.append(Population.load(db))

        for x in range(args.loops):
            ga_run(ga_input)

    elif 'KEYWORD' in dir(args):
        InputHelp(args.KEYWORD)
