from .ga_progress import GAProgress

class FunctionData:
    """
    Stores information about functions and their parameters.

    Attributes
    ----------
    name : str
        The name of a function or method.

    params : dict
        The parameters of the function or method who's name is held by
        'name' which should be used when that function is called.
    
    """
    
    __slots__ = ['name', 'params']    
    
    def __init__(self, name, **kwargs):
        self.name = name
        self.params = kwargs
        
    def __repr__(self):
        return ("<FunctionData, name={}"
                ", params={}>").format(self.name, self.params)
        
    def __str__(self):
        return ("<FunctionData, name = {}"
                ", params = {}>").format(self.name, self.params)
        
class GATools:
    """
    Stores objects which carry out GA operations on populations.
    
    Instances of this class are held by ``Population`` instances in
    their `ga_tools` attribute. All the instances which carry out GA
    operations on the population are held conveniently together in an 
    instance of this class. The optimization function used by the GA
    is also stored here as is the fitness function.

    Attributes
    ----------
    selection: Selection
        The ``Selection`` instance which performes selections of a 
        population's members.
    
    mating : Mating
        The ``Mating`` instance which mates a population's members.
    
    mutation : Mutation
        The ``Mutation`` instance which mutates a population's members
        
    optimization : FuncionData
        Holds the name of the function in ``optimization.py`` to be 
        used for ``MacroMolecule`` optimizations and any additional 
        parameters the function may require.
        
    fitness : FunctionData
        Holds the name of the function in ``fitness.py`` to be used for
        calculating the fitness of ``MacroMolecule`` instances. It also
        holds any additional paramters the function may require.
    
    ga_input : GAInput
        The GAInput object holding data gathered from the input file.
        This attribute is added in the ``__main__.py`` script.
    
    """
    
    __slots__ = ['selection', 'mating', 'mutation', 
                 'optimization', 'fitness', 'ga_input', 'ga_progress']    
    
    def __init__(self, selection, mating, 
                 mutation, optimization, fitness):
        self.selection = selection
        self.mating = mating
        self.mutation = mutation
        self.optimization = optimization
        self.fitness = fitness
        self.ga_progress = GAProgress()
