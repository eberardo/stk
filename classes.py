import numpy as np
from functools import wraps
from operator import attrgetter
import itertools
import weakref
from convenience_functions import dedupe
from rdkit import Chem as chem
from rdkit.Chem import AllChem as ac
from collections import namedtuple
from operator import attrgetter
from copy import deepcopy

class Cached(type):   
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)        
        self.__cache = weakref.WeakValueDictionary()
    
    def __call__(self, *args):
        if args in self.__cache.keys():
            return self.__cache[args]
        else:
            obj = super().__call__(*args)
            self.__cache[args] = obj
            return obj

class MoleculeData(object):
    """ class to store info about a molecule """
    def __init__(self, id_ = 0, name = "", number = 0, atoms = None, bonds= None,
                 tot_atoms = 0, heavy_atoms = 0, elements = None, coordinates = None,
                 trasl_coordinates = None, rot_coordinates = None, heavy_atom_idx = None):
        self.id = id_
        self.name = name
        self.number = number
        self.tot_atoms = tot_atoms
        self.heavy_atoms = heavy_atoms
        self.elements = elements
        self.coordinates = coordinates
        self.trasl_coordinates = trasl_coordinates
        self.rot_coordinates = rot_coordinates
        self.heavy_atom_idx = heavy_atom_idx
        
        if atoms == None:
            self.atoms = {}
        else:
            self.atoms = atoms
        
        if bonds == None:
            self.bonds = []
        else:
            self.bonds = bonds

        if elements == None:
            self.elements = []
        else:
            self.elements = elements
            
        if coordinates == None:
            self.coordinates = []
        else:
            self.coordinates = np.array(coordinates)
            
        if heavy_atom_idx == None:
            self.heavy_atom_idx = []
        else:
            self.heavy_atom_idx = heavy_atom_idx



FGInfo = namedtuple('FGInfo', ['name', 'smarts', 
                               'target_atomic_num', 'heavy_atomic_num',
                               'heavy_symbol'])
class StructUnit:
    functional_group_list = [
                        
                    FGInfo("aldehyde", "C(=O)[H]", 6, 39, "Y"), 
                    FGInfo("carboxylic acid", "C(=O)O[H]", 6, 40, "Zr"),
                    FGInfo("amide", "C(=O)N([H])[H]", 6, 41, "Nb"),
                    FGInfo("thioacid", "C(=O)S[H]", 6, 42, "Mo"),
                    FGInfo("alcohol", "O[H]", 8, 43, "Tc"),
                    FGInfo("thiol", "[S][H]", 16, 44, "Ru"),
                    FGInfo("amine", "[N]([H])[H]", 7, 45, "Rh"),    
                    FGInfo("nitroso", "N=O", 7, 46, "Pd"),
                    FGInfo("boronic acid", "[B](O[H])O[H]", 5, 47, "Ag")
                             
                             ]

    def __init__(self, prist_mol_file):
        self.prist_mol_file = prist_mol_file
        self.prist_mol = chem.MolFromMolFile(prist_mol_file, 
                                             sanitize=False, 
                                             removeHs=False)
                                             
        self.prist_smiles = chem.MolToSmiles(self.prist_mol, 
                                             isomericSmiles=True,
                                             allHsExplicit=True)

    def find_functional_group_atoms(self, functionality):
        """


        """        
        
        func_grp = next((x for x in StructUnit.functional_group_list if 
                                        x.name == functionality), None)
                          
        func_grp_mol = chem.MolFromSmarts(func_grp.smarts)
        return self.prist_mol.GetSubstructMatches(func_grp_mol)
       

    def generate_heavy_mol(self, functionality):

        func_grp = next((x for x in StructUnit.functional_group_list if 
                                        x.name == functionality), None)        
        matches = self.find_functional_group_atoms(functionality)       

        heavy_mol = deepcopy(self.prist_mol)      
        
        for func_grp_ids in matches:
            for atom_id in func_grp_ids:
                atom = heavy_mol.GetAtomWithIdx(atom_id)
                if atom.GetAtomicNum() == func_grp.target_atomic_num:
                    atom.SetAtomicNum(func_grp.heavy_atomic_num)
        
        self.heavy_mol = heavy_mol
        chem.MolToMolFile(heavy_mol, )
        self.heavy_mol_file = 
        self.heavy_smiles =         
        
        
class BuildingBlock(StructUnit):
    pass
        
class Linker(StructUnit):
    pass

class Cage(metaclass=Cached):
    def __init__(self, *args):
        if len(args) == 3:
            self.testing_init(*args)

    def std_init(self, bb_smiles, lk_smiles, topology):
        self.bb = BuildingBlock(bb_smiles)
        self.lk = Linker(lk_smiles)        
        self.topology = topology
        
    def bb_only_init(self, ):
        pass
    def lk_only_init(self, ):
        pass
    
    def same_cage(self, other):
        return (self.bb == other.bb and self.lk == other.lk and 
                                    self.topology == other.topology)
        
    def __str__(self):
        return str(self.__dict__) + "\n"
    
    def __repr__(self):
        return str(self.__dict__) + "\n"


    
    def build_cage(outputfile, shape, bb_smile, bb_func, lk_smile = "",
                  lk_func = None):
        """This function is the one which prepares all the conditions for the 
        assembly. 
        ==========================================================================
        Parameters:
            shape = Topology employed to build the cage (defined in the topology.py 
                    module)
            bb_smile = string containing the SMILE for the building block
            bb_func = Code used to characterize the functional group to be
                                substituted (defined in GA_rdkit_functions.py)
            lk_smile = string containing the SMILE for the linker
                        (Default is empty, "")*
            lk_func = Code used to characterize the functional group to be
                                substituted (defined in GA_rdkit_functions.py).
                                Default is None.*
            outputfile = name of the outputfile
            
            *Default values for the linker are "" and None as the user can decide to
            generate a cage where no linker is employed (both vertices and edges
            are occupied by the same molecule)
            
        Returns:
            heavy_atom_file?
            bb_num?
            bb_heavy_atom_count?
            lk_num?
            lk_heavy_atom_count?
        ==========================================================================
        
        1) Read in the smiles
        2) Knows which are the functions to substitute/modify with heavy atoms
        3) Generates the bb_heavy.mol and lk_heavy.mol files
        4) Calls the assembly function, which produces the heavy_atom cage
        5) Reads the file in and creates bonds between the heavy atoms (addition)
        6) Substitutes the final atoms in the final cage (final_sub)
        
        """
        
        # Reading in the SMILES create the bb_new.mol and lk_new.mol files
        # Apply the FlagFunctionalGroupAtom 
        # First to Building Block
        with open("bb_mol.mol", "w") as bb_input:
            bb_input.write(grf.FlagFunctionalGroupAtom(bb_smile, bb_func)[0])
        
        # Create flags to substitute functional groups with heavy atoms
        bb_flag = grf.FlagFunctionalGroupAtom(bb_smile, bb_func)[1]
        bb_read = readmol.Mol("bb_mol.mol")
        bb_mol = bb_read.molecules
        # Generates a new mol file containing the heavy atoms
        bb_heavy_atom = grf.GenerateHeavyFile(bb_mol, bb_flag, "bb_heavy.mol")[0]
        bb_heavy_atom_count = grf.GenerateHeavyFile(bb_mol, bb_flag, "bb_heavy.mol")[1]
        # Then to the Linker if lk_smile != "" and lk_func != None
        if lk_smile != "" and lk_func != None:
            with open("lk_mol.mol", "w") as lk_input:
                lk_input.write(grf.FlagFunctionalGroupAtom(lk_smile, lk_func)[0])
            lk_input.close()
            # Create flags to substitute functional groups with heavy atoms
            lk_flag = grf.FlagFunctionalGroupAtom(lk_smile, lk_func)[1]
            lk_read = readmol.Mol("lk_mol.mol")
            lk_mol = lk_read.molecules
            # Generates a new mol file containing the heavy atoms
            lk_heavy_atom = grf.GenerateHeavyFile(lk_mol, lk_flag, "lk_heavy.mol")[0]
            lk_heavy_atom_count = grf.GenerateHeavyFile(lk_mol, lk_flag, "lk_heavy.mol")[1]         
        else:
            pass
        
        
        # Apply the assemble_bb_lk function
        a = assemble_bb_lk(shape)
        bb_num = assemble_bb_lk(shape)[2]
        lk_num = assemble_bb_lk(shape)[3]
        # Save assembled system to outputfile
        readmol.write_mol(a[0], a[1], outputfile)
        
        # Creating the heavy atom file
        heavy_atom_file_name = outputfile[:-4] + "HEAVY.mol"
        
        # Create final bonds between bb and lk in the assembled file
        grf.AdditionDifferent(outputfile, bb_heavy_atom, bb_heavy_atom_count,
                              lk_heavy_atom, lk_heavy_atom_count, heavy_atom_file_name,
                              shape)
        # Final substitution of heavy atoms with the correct atoms
        grf.final_sub(heavy_atom_file_name, outputfile)
        
    #    print("BB_NUM", bb_num, "LK_NUM", lk_num)
    #    print("BB SUB ATOMS", bb_heavy_atom_count, "LK SUB ATOMS", lk_heavy_atom_count)
        return  heavy_atom_file_name, bb_num, bb_heavy_atom_count, lk_num, lk_heavy_atom_count


    """
    The following methods are inteded for convenience while 
    debugging or testing and should not be used during typical 
    execution of the program.
    
    """

    def testing_init(self, bb_str, lk_str, topology_str):
        self.bb = bb_str
        self.lk = lk_str
        self.topology = topology_str

    @classmethod
    def init_empty(cls):
        obj = cls()
        string = ['a','b','c','d','e','f','g','h','i','j','k','l','m',
                  'n','o', 'p','q','r','s','t','u','v','w','x','y','z']
        obj.bb = np.random.choice(string)
        obj.lk = np.random.choice(string)
        obj.fitness = abs(np.random.sample())
        return obj

class FunctionData:
    def __init__(self, name, **kwargs):
        self.name = name
        self.params = kwargs
        
class GATools:
    def __init__(self, selection, mating, mutation):
        self.selection = selection
        self.mating = mating
        self.mutation = mutation
        
    @classmethod
    def default(cls):
        return cls(Selection.default(),2,3)

class Selection:
    def __init__(self, generational, mating, mutation):
        self.generational = generational
        self.mating = mating
        self.mutation = mutation
    
    @classmethod
    def default(cls):
        func_data = FunctionData('fittest', size=5)
        return cls(*[func_data for x in range(0,3)])
    
    def __call__(self, population, type_):
        func_data = self.__dict__[type_]
        func = getattr(self, func_data.name)
        return func(population, **func_data.params)        

    def fittest(self, population, size):        
        if len(population) < size:
            raise ValueError(("Size of selected population" 
                              " must be less than or equal to" 
                              " size of original population."))                           
        
        ordered_pop = list(population.all_members())
        ordered_pop.sort(key=attrgetter('fitness'), reverse=True)    
        return Population(population.ga_tools, *ordered_pop[:size])
        
    def roulette(self, population):
        pass
    
    def all_combinations(self, population):
        pass

class Mating:
    def __init__(self, func_data):
        self.func_data = func_data
    
    def __call__(self, population):
        parent_pool = population.select('mating')
        offsprings = Population(population.ga_tools)
        func = getattr(self, self.func_data.name)
        
        for parents in parent_pool.populations:
            offspring = func(*parents, **self.func_data.params)
            offsprings.add_members(offspring)

        offsprings -= population
            
        return offsprings
        
    def bb_lk_exchange(self, cage1, cage2, _):
        ...

class Mutation:
    def __init__(self):
        pass

class Population:
    """
    A container for instances of ``Cage`` and ``Population``.

    This is the central class of MMEA. The GA is invoked by calling the
    ``gen_offspring``, ``gen_mutants`` and ``select`` methods of this 
    class on a given instance. However, this class is a container of 
    ``Cage`` and other ``Population`` instances first and foremost. It 
    delegates GA operations to its `ga_tools` attribute. Any 
    functionality related to the GA should be delegated to this 
    attribute. The ``gen_offspring`` and ``gen_mutants`` methods can 
    serve as a guide to how this should be done. A comphrehensive 
    account of how the interaction between these two classes is provided 
    in the developer's guide.
    
    For consistency and maintainability, collections of ``Cage`` or 
    ``Population`` instances should always be placed in a ``Population`` 
    instance. As a result, any function which should return multiple 
    ``Cage`` or ``Population`` instances can be expected to return a 
    single ``Population`` instance holding the desired instances. Some 
    functions will have to return the population organized in a specific 
    way. For example, functions generating the parent pool will generate 
    a population with no direct members but multiple subpopulations of 2 
    members each. More specific guidelines are provided within the 
    ``Mating`` class.
    
    The only operations directly addressed by this class and definined 
    within it are those relevant to its role as a container. It supports
    all expected and necessary container operations such as iteration, 
    indexing, membership checks (via the ``is in`` operator) as would be 
    expected. Additional operations such as comparison via the ``==``, 
    ``>``, etc. operators is also supported. Details of the various 
    implementations and a full list of supported operations can be found 
    by examining the included methods. Note that all comparison 
    operations are accounted for with the ``total_ordering`` decorator, 
    even if they are not explicity defined.

    Attributes
    ----------
    populations : list
        A list of other instances of the ``Population`` class. This
        allows the implementation of subpopulations or 'evolutionary 
        islands'. This attribute is also used for grouping cages within
        a given population such as when grouping parents together in a 
        parent pool.
        
    members : list
        A list of ``Cage`` instances. These are the members of the
        population which are not held within any subpopulations. This 
        means that not all members of a population are stored here. 
        To access all members of a population the generator method 
        ``all_members`` should be used.
    
    ga_tools : GATools, optional
        An instance of the ``GATools`` class. Calls to preform GA
        operations on the ``Population`` instance are delegated 
        to this attribute.
    
    """
    
    def __init__(self, *args):
        """
        Initializer for ``Population`` class.
        
        This initializer creates a new population from the 
        ``Population`` and ``Cage`` instances given as arguments.
        It also accepts a single, optional, ``GATools`` instance if the 
        population is to have GA operations performed on it.
        
        The arguments can be provided in any order regardless of type.
        
        Parameters
        ----------
        *args : Cage, Population, GATools
            A population is initialized with as many ``Cage`` or 
            ``Population`` arguments as required. These are placed into 
            the `members` or `populations` attributes, respectively. 
            A single ``GATools`` instance may be included and will be
            placed into the `ga_tools` attribute. 
        
        Raises
        ------
        TypeError
            If the instance is initialized with something other than
            ``Cage``, ``Population`` or more than 1 ``GATools`` object. 
            
        """    
        
        # Generate `populations`, `members` and `ga_tools` attributes.
        self.populations = []
        self.members = []
        self.ga_tools = None
    
        # Determine type of supplied arguments and place in the
        # appropriate attribute.  ``Population`` types added to
        # `populations` attribute, ``Cage`` into `members` and if
        # ``GATools`` is supplied it is placed into `ga_tools`.
        # Raise a ``TypeError`` if more than 1 ``GATools`` argument
        # was supplied or if an argument was not ``GATools``, ``Cage`` 
        # or ``Population`` type.
        for arg in args:
            if type(arg) is Population:
                self.populations.append(arg)
                continue
            
            if type(arg) is Cage:
                self.members.append(arg)
                continue           
            
            if type(arg) is GATools and self.ga_tools is None:
                self.ga_tools = arg
                continue

            # Some methods create a new ``Population`` instance by using 
            # another as a template. In these cases the `ga_tools` 
            # attribute of the template population is passed to the 
            # initializer. If the template instance did not have a 
            # defined ``GATools`` instance, the default ``None`` 
            # argument is passed. The following 2 lines prevent 
            # exceptions being raised in such a scenario. A consequence
            # of this is that any number of ``None`` arguments can be 
            # passed to the initializer. 
            if arg is None:
                continue

            raise TypeError(("Population can only be"
                             " initialized with 'Population',"
                             " 'Cage' and 1 'GATools' type."), arg)
                                    
    def all_members(self):
        """
        Yields all members in the population and its subpopulations.

        Yields
        ------
        Cage
            The next ``Cage`` instance held within the population or its
            subpopulations.
        
        """
        
        # Go through `members` attribute and yield ``Cage`` instances
        # held within one by one.
        for ind in self.members:
            yield ind
        
        # Go thorugh `populations` attribute and for each ``Population``
        # instance within, yield ``Cage`` instances from its
        # `all_members()` generator.
        for pop in self.populations:
            yield from pop.all_members()
            
    def add_members(self, population, duplicates=False):
        """
        Adds ``Cage`` instances into `members`.        
        
        The ``Cage`` instances held within the supplied ``Population`` 
        instance, `population`, are added into the `members` attribute 
        of `self`. The supplied `population` itself is not added. This 
        means that any information the `population` instance had about 
        subpopulations is lost. This is because all of its ``Cage`` 
        instances are added into the `members` attribute, regardless of 
        which subpopulation they were originally in.

        The `duplicates` parameter indicates whether multiple instances
        of the same cage are allowed to be added into the population.
        Note that the sameness of a cage is judged by the `same_cage`
        method of the ``Cage`` class, which is invoked by the ``in``
        operator within this method. See the `__contains__` method of 
        the ``Population`` class for details on how the ``in`` operator 
        uses the `same_cage` method.
        
        Parameters
        ----------
        population : Population
            ``Cage`` instances to be added to the `members` attribute
            and/or ``Population`` instances who's members, as generated 
            by `all_members`, will be added to the `members` attribute.
        
        duplicates : bool (default = False)
            When `False` only cages which are not already held by
            the population will be added. `True` allows more than one
            instance of the same cage to be added. Whether two cages
            are the same is defined by the `same_cage` method of the
            ``Cage`` class.
        
        """
        
        if duplicates:
            self.members.extend(cage for cage in population)
        else:
            self.members.extend(cage for cage in population
                                                    if cage not in self)
    def add_subpopulation(self, population):
        """
        Appends a population into the `populations` attribute.        
        
        Parameters
        ----------
        population : Population
            The population to added as a subpopulation.
            
        Returns
        -------
        None : NoneType
        
        """
        
        self.populations.append(population)
        
    def remove_duplicates(self, between_subpops=True, top_seen=None):
        """
        Removes duplicates from a population while preserving structure.        
        
        The question of which ``Cage`` instance is preserved from a 
        choice of two is difficult to answer. The iteration through a 
        population is depth-first so a rule such as ``the cage in the
        topmost population is preserved`` is not possible to define. 
        However, this question is only relevant if duplicates are being 
        removed from between subpopulations. In this case it is assumed 
        that the fact that only a single instance is present is more 
        important than which one. As a result it should be of no 
        consquence which cage is preserved from two different 
        subpopulations. This is however may be subject to change.
        
        Parameters
        ----------
        between_subpops : bool (default = False)
            When ``False`` duplicates are only removed from within a
            given subpopulation. If ``True`` all duplicates are removed,
            regardless of which subpopulation they are in.
            
        Returns
        -------
        None : NoneType
        
        """
        
        if between_subpops:
            if top_seen is None:
                seen = set()
            if type(top_seen) == set:
                seen = top_seen
                
            self.members = list(dedupe(self.members, seen=seen))
            for subpop in self.populations:
                subpop.remove_duplicates(between_subpops, top_seen=seen)
        
        if not between_subpops:
            self.members = list(dedupe(self.members))
            for subpop in self.populations:
                subpop.remove_duplicates(between_subpops=False)
        
    def select(self, type_='generational'):
        """
        Selects some members to form a new ``Population`` instance.
        
        Selection is a GA procedure and as a result this method merely 
        delegates the selection request to the ``Selection`` instance 
        held within the `ga_tools` attribute. The ``Selection`` instance
        then returns the new ``Population`` instance. This 
        ``Population`` instance is then returned by this method.
        The selection instance (`self.ga_tools.selection`) performs the
        selection by being called. See ``Selection`` class documentation
        for more information.
        
        Because selection is required in a number of different ways,
        such as selecting the parents, ``Cage`` instances for mutation
        and ``Cage`` instances for the next generation, the type of 
        selection must be specificed with the `type_` parameter. The
        valid values for `type_` will correspond to one of the
        attribute names of the ``Selection`` instance.

        For example, if `type_` is set to 'mating' a selection 
        algorithm which creates a parent pool will be invoked. If the 
        `type_` is set to 'generational' an algorithm which selects the 
        next generation will be invoked. It should be noted that a 
        ``Population`` instance representing a parent pool will be
        organized differently to one representing a generation. See
        ``Selection`` class documentation for more details.
        
        The information regarding which generational, parent pool, etc.
        algorithm is used is held by the ``Selection`` instance. This 
        method merely requests that the ``Selection`` instance performs 
        the selection algorithm of the relevant type. The ``Selection`` 
        instance takes care of all the details to do with selection.
        
        Parameters
        ----------
        type_ : str (default = 'generational')
            A string specifying the type of selection to be performed.
            Valid values will correspond to names of attributes of the 
            ``Selection`` class. Check ``Selection`` class documentation
            for details. 
            
            Valid values include:              
                'generational' - selects the next generation
                'mating' - selects parents
                'mutation' - selects ``Cage`` instances for mutation

        Returns
        -------        
        Population
            A population generated by using applying a selection
            algorithm. Can represent a generation, a parent pool, etc.
        
        """
        
        return self.ga_tools.selection(self, type_)
        
    def gen_offspring(self):
        """
        Returns a population of offspring ``Cage`` instances.        
        
        This is a GA operation and as a result this method merely
        delegates the request to the ``Mating`` instance held in the 
        `ga_tools` attribute. The ``Mating`` instance takes care of 
        selecting parents and combining them to form offspring. The
        ``Mating`` instace delegates the selection to the ``Selection`` 
        instance as would be expected. The request to perform mating is 
        done by calling the ``Mating`` instance with the population as 
        the argument. Calling of the ``Mating``instance returns a 
        ``Population`` instance holding the generated offspring. All 
        details regarding the mating procedure are handled by the 
        ``Mating`` instance.

        For more details about how mating is implemented see the
        ``Mating`` class documentation.
        
        Returns
        -------
        Population
            A population holding offspring created by mating contained 
            the ``Cage`` instances.
        
        """
        
        return self.ga_tools.mating(self)
        
    def gen_mutants(self):
        """
        Returns a population of mutant ``Cage`` instances.        
        
        
        
        Returns
        -------
        Population
            A population holding mutants created by mutating contained
            ``Cage`` instances.
        
        """

        return self.ga_tools.mutation(self)
        
    def __iter__(self):
        """
        Allows the use of ``for`` loops, ``*`` and ``iter`` function.        

        When ``Population`` instances are iterated through they yield 
        ``Cage`` instances generated by the `all_members` method. It 
        also means that a ``Population`` instance can be unpacked with
        the ``*`` operator. This will produce the ``Cage`` instances
        yielded by the `all_members` method.

        Returns
        -------
        Generator
            The `all_members` generator. See `all_members` method 
            documentation for more information.
        
        """
        
        return self.all_members()
            
    def __getitem__(self, key):
        """
        Allows the use of ``[]`` operator.

        Cages held by the ``Population`` instance can be accesed by
        their index. Slices are also supported. These return a new
        ``Population`` instance holding the ``Cage`` instances with
        the requested indices. Using slices will return a flat 
        ``Population`` instance meaing no subpopulation
        information is preserved. All of the ``Cage`` instances are
        placed into the `members` attribute of the returned 
        ``Population`` instance.

        The index corresponds to the ``Cages`` yielded by the 
        `all_members` method.

        This can be exploited if one desired to remove all
        subpopulations and transfer all the ``Cage`` instances into the 
        members attribute. For example, 
        
        >>> pop2 = pop[:]
        
        ``pop2`` is a ``Population`` instance with all the same
        ``Cage`` instances as ``pop``, however all ``Cage`` 
        instances are held within its `members` attribute and its 
        `populations` attribute is empty. This may or may not be the 
        case for the ``pop`` instance.   
        
        Parameters
        ----------
        key : int, slice
            An int or slice can be used depending on if a single 
            ``Cage`` instance needs to be returned or a collection of 
            ``Cage`` instances.
        
        Returns
        -------
        Cage
            If the supplied `key` is an ``int``. Returns the ``Cage`` 
            instance with the corresponding index from the `all_members` 
            generator.
        
        Population
            If the supplied `key` is a ``slice``. The returned 
            ``Population`` instance holds ``Cage`` instances in its 
            `members` attribute. The ``Cage`` instances correspond to 
            indices defined by the slice. The slice is implemented 
            on the `all_members` generator.
        
        Raises
        ------
        TypeError
            If the supplied `key` is not an ``int`` or ``slice`` type.        
        
        """
        
        # Determine if provided key was an ``int`` or a ``slice``.
        # If ``int``, return the corresponding ``Cage`` instance from
        # the `all_members` generator.
        if type(key) is int:
            return list(self.all_members())[key]
        
        # If ``slice`` return a ``Population`` of the corresponding 
        # ``Cage`` instances. The returned ``Population`` will have the 
        # same `ga_tools` attribute as original ``Population`` instance.        
        if type(key) is slice:
            cages = itertools.islice(self.all_members(), 
                                     key.start, key.stop, key.step)
            return Population(*cages, self.ga_tools)

        # If `key` is not ``int`` or ``slice`` raise ``TypeError``.        
        raise TypeError("Index must be an integer or slice, not"
                        " {}.".format(type(key).__name__))
        
    def __len__(self):
        """
        Returns the number of members yielded by `all_members`.

        Returns
        -------
        int
            The number of members held by the population, including
            those held within its subpopulations.
        
        """

        return len(list(self.all_members()))
        
    def __sub__(self, other):
        """
        Allows use of the ``-`` operator.
        
        Subtracting one from another,

            pop3 = pop1 - pop2,        
        
        returns a new population, pop3. The returned population contains 
        all the ``Cage`` instances in pop1 except those also in pop2.
        This refers to all of the ``Cage`` instances, including those
        held within any subpopulations. The returned population is 
        flat. This means all information about subpopulations in pop1 is 
        lost as all the ``Cage`` instances are held in the `members` 
        attribute of pop3.

        The resulting population, pop3, will inherit the `ga_tools` 
        attribute from pop1.

        Parameters
        ----------
        other : Population
            A collection of ``Cage`` instances to be removed from 
            `self`, if held by it.
            
        Returns
        -------
        Population
            A flat population of ``Cage`` instances which are not also
            held in `other`.

        """

        new_pop = Population(self.ga_tools)        
        new_pop.add_members(cage for cage in self 
                                                if cage not in other)
        return new_pop
        
    def __add__(self, other):
        """
        Allows use fo the ``+`` operator.
        
        Parameters
        ----------
        other : Population
        
        Returns
        -------
        Population

        
        """
        
        return Population(self, other, self.ga_tools)

    def __contains__(self, item):
        """
        Allows use of the ``in`` operator.

        Parameters
        ----------
        item : Cage

        Returns
        -------
        bool
        
        """

        return any(item.same_cage(cage) for cage in self.all_members())

    def __str__(self):
        output_string = (" Population " + str(id(self)) + "\n" + 
                            "--------------------------\n" + 
                            "\tMembers\n" + "   ---------\n")
        
        for cage in self.members:
            output_string += "\t"  + str(cage) + "\n"
        
        if len(self.members) == 0:
            output_string += "\tNone\n\n"
        
        output_string += (("\tSub-populations\n" + 
                           "   -----------------\n\t"))
        
        for pop in self.populations:
            output_string += str(id(pop)) + ", "

        if len(self.populations) == 0:
            output_string += "None\n\n"
        
        output_string += "\n\n"

        for pop in self.populations:
            output_string += str(pop)

        
        return output_string
        
    def __repr__(self):
        return str(self)

    """
    The following methods are inteded for convenience while 
    debugging or testing and should not be used during typical 
    execution of the program.
    
    """

    @classmethod
    def init_empty(cls):
        pops = []
        
        for x in range(0,8):
            pop = cls(*iter(Cage.init_empty() for x in range(0,3)), 
                      GATools.default())
            pops.append(pop)
        
        pops[1].populations.append(pops[3])
        pops[1].populations.append(pops[4])
        pops[1].populations.append(pops[5])
        
        pops[2].populations.append(pops[6])
        pops[2].populations.append(pops[7])
        
        pops[0].populations.append(pops[1])
        pops[0].populations.append(pops[2])        
        
        return pops[0]
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        