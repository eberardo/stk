import numpy as np
import rdkit.Chem as chem
import itertools as it
import copy
from inspect import signature

from .classes.exception import MacroMolError
from .classes.molecular import MacroMolecule, StructUnit
from . import optimization
from .convenience_functions import rotation_matrix_arbitrary_axis

def calc_fitness(func_data, population):
    """
    Calculates the fitness values of all members of a population.
    
    A fitness function should take a ``MacroMolecule`` instance and
    return a number representing its fitness. The assignement to the
    `fitness` attribute of a population member happens here, not by the
    fitness function.    
    
    Extending MMEA: Adding fitness functions
    ----------------------------------------
    To add a new fitness function simply write it as a function in this
    module. It will need to take the ``MacroMolecule`` instance as its
    first argument. 
    
    Some fitness functions will need to have certain internal values 
    normalized. In this section, the ``cage`` fitness function is used
    as an example.
    
    The cage fitness function has the form
    
        (1) fitness = A*(var1^a) + B(var2^b) + C(var3^c) + D(var4^d).
        
    Here var1 to var4 represent the parameters of a cage which factor
    into its fitness. If raw values of these parameters are used, due
    to different units and naturally different orders of magnitude one
    parameter may have an undue influence on the fitness only because
    of its units. The goal is for fitness function contributions to be
    determined soley by the coeffiecients A to D and exponents a to d.
    
    In order to do this the average value of var1 throughout the entire
    population is calculated first and then used as a scaling factor.
    The variables in the fitness function therefore have the form
    
        (2) var = var_ind / <var>,
        
    where var can be any of var1 to var4 in equation (1), var_ind is the
    variable of for that individual and <var> is the average of that 
    variable throughout the population.
    
    In order to calculate the fitness in this way the fitness function
    needs to be applied twice to each member of the population. The
    first loop calculates var_ind and <var> and the second loop 
    calculates var. See the implementation.
    
    Fitness functions which require this scaling procedure will need to
    have a keyword argument called `means` which is default initialized
    to ``None``. In order to make use of this they will also have to
    have the general form of equation (1). Nothing else is reqiured
    but they should allow the user to supply array holding the c
    oefficients and exponents. See the implementation of ``cage``.
    
    Parameters
    ----------
    func_data : FunctionData
        A ``FunctionData`` instance representing the chosen fitness 
        function and any additional parameters it may require.
    
    population : Population
        The population whose members must have their fitness calculated.
        
    Returns
    -------
    None : NoneType    
    
    """

    # Get the fitness function object.
    func = globals()[func_data.name]
    
    # Some fitness functions will normalize various fitness parameters
    # across the population. If this is to be done a ``means`` parameter
    # should be found in the signature of the function.
    use_means = 'means' in signature(func).parameters.keys() 
    
    # This carries out the first part normalization procedure, if 
    # needed. This is the calculation of the mean value of a each
    # fitness parameter in the population. For example, if the ``cage``
    # fitness function is being used the mean values of `asymmetry`,
    # `cavity_diff` (and so on) are found. These average values are then
    # stored with the population in its `ga_tools` attribute.
    if use_means:
        # In order to calculate the mean, first you calculate the sum
        # and then divide by the number of things summed. `var_sum` is
        # an array where each element is the sum of a particular fitness
        # parameter across the population. It is initialized to 0 but 
        # turns into an array later.
        var_sum = 0
        # `valid_params` is the count of how many sets of fitness 
        # parameter arrays were added together. The fitness function may 
        # fail on a particlar molecule and as a result its unscaled 
        # fitness parameters are not added to `var_sum`. This means that
        # the individual will not contribute to the number of things
        # summed either.
        valid_params = 0
        for ind in population:
            # Try running the fitness function on the individual. If it
            # excepts just set the `unscaled_fitness_vars` attribute to 
            # ``None`` and the `unscaled` variable to ``None``. If the
            # function does not except it means two things. The
            # individual will have an attribute `unscaled_fitness_vars`
            # holding an array contaninig the fitness paramters. This
            # will also be what is returned by the function and placed
            # into the `unscaled` variable. If this happens the
            # `unscaled` variable is added to `var_sum` and 
            # `valid_params` is incremented by 1.
            try:
                unscaled = func(ind, **func_data.params)

            except Exception as ex:
                ind.unscaled_fitness_vars = None
                unscaled = None
            
            if unscaled is not None:
                valid_params += 1
                var_sum = np.add(unscaled, var_sum)

        # To get the average divide the sum by the number of things 
        # summed.
        var_avg = np.divide(var_sum, valid_params)

    # Apply the function to every member of the population.
    for macro_mol in population:
        try:
            # If `use_means` is ``True``, the fitness function should
            # have a `means` parameter. This parameter should be set to
            # the variable `var_avg` calculated above. This normalizes
            # all of the fitness paramters.
            if use_means:
                macro_mol.fitness = func(macro_mol, means=var_avg,
                                         **func_data.params)
            
            # If `use_means` is not ``True`` no need to provide the
            # `means` argument.            
            else:
                macro_mol.fitness = func(macro_mol, **func_data.params)
                
        except Exception as ex:
            MacroMolError(ex, macro_mol, 'During fitness calculation.')

    # After each macro_mol has a fitness value, sort the population by 
    # fitness and print.
    for macro_mol in sorted(population, reverse=True):
        print(macro_mol.fitness, '-', macro_mol.prist_mol_file)
            
def random_fitness(macro_mol):
    """
    Returns a random fitness value between 1 and 10.

    Parameters
    ----------
    macro_mol : MacroMolecule
        The macromolecule to which a fitness value is to be assigned.
    
    Returns
    -------
    int
        An integer between 0 (including) and 100 (excluding).

    """

    return np.random.randint(1,10)

def param_labels(*labels):
    """
    Adds `param_labels` attribute to a fitness function.
    
    Fitness functions which undergo the scaling procedure have an EPP 
    graph plotted for each attribute used to calculate total fitness. 
    For example, if the ``cage`` fitness function was used
    during the GA run 5 graphs would be plotted at the end of the run.
    One for each unscaled ``var`` (see ``cage`` documentation for more 
    details). This plotting is done by the ``GAProgress`` class. 
    
    In order for the ``GAProgress`` class to produce decent graphs, 
    which means that each graph has the y-axis and title labeled with 
    the name of the ``var`` plotted, it needs to know what each ``var`` 
    should be called.
    
    This is done by adding a `param_labels` attribute to the fitness
    function. The ``GAProgress`` class acccesses this attribute during
    plotting and uses it to set the y-axis / title.
    
    Parameters
    ----------
    labels : tuple
        List of strings about the fitness labels used for plotting EPPs.
        The order of the strings should represent the order of the
        fitness ``vars`` in the fitness funciton. In practice it should
        correspond to the order of the ``coeffs`` or ``exponents`` 
        parameters given to the fitness function.
    
    Returns
    -------
    func
        Decorated function.
        
    """
    
    def add_labels(func):
        func.param_labels = labels    
        return func
        
    return add_labels

# Calls the decorator with the specific labels
@param_labels('Cavity Difference ','Window Difference ',
                'Asymmetry ', 'Negative Energy per Bond ', 
                'Positive Energy per Bond ')
def cage(macro_mol, target_cavity, macromodel_path, 
         target_window=None, coeffs=None, exponents=None, means=None):
    """
    Calculates the fitness of a cage.
    
    The fitness function has the form
    
        (1) fitness = penalty_term + carrot_term
        
    where
        
        (2) penalty_term = 1 / [ A*(var1^a) + B*(var2^b) + C*(var3^c) + 
                                 D*(var4^d) ],
                                 
    and 
    
        (3) carrot_term = E*(var5^e).
        
    Here var1 to var5 signify parameters of the cage which factor into
    fitness. These parameters are calculated by the fitness function and
    placed in variables, for example:
        
        1) `cavity_diff` - the difference between the cage's cavity
           (diameter) and the desired cavity size
        2) `window_diff` - the difference between the diameter of the 
           window of the cage and the size required to allow the target
           to enter the cavity
        3) `asymmetry` - sum of the difference between the size of the
           windows of the same type
        4) `neg_eng_per_bond` - the formation energy of the cage divided 
           by the number of bonds for during assembly, when the energy
           is < 0. This is a measure of the stability or strain of a 
           cage.
        5) Same as 4) but used when the energy is > 0.
        
    The design of the fitness function is as follows. Consider two
    cages, ``CageA`` and ``CageB``. If the parameters, 1) to 4), in
    CageA, which signify poor fitness are 10 times that of CageB and the
    parameter which signifies good fitness, 5), is 10 times less than 
    CageB, then CageA should have a fitness value 10 times less than 
    CageB.
    
    This is assuming all coefficients and powers are 1. Note that a cage
    will always have either 4) or 5) at 0. This is because its total 
    energy will always be either positive or negative.
    
    The `coeffs` parameter has the form
    
        np.array([1,2,3,4,5]),

    where 1, 2, 3, 4 and 5 correspond to the desired values of A, B, C,  
    D and E in equation (2). Equally the `exponents` parameter also has 
    the form

        np.array([5,6,7,8,9]),
    
    where 5, 6, 7, 8 and 9 correspond to the values of a, b, c, d and e
    in equation (2).
    
    Assume that for a given GA run, it is not worthwhile factoring in 
    the `window_diff` parameter. This may be because cages which 
    form via templating are also to be considered. If the cage forms
    around the target, its windows size is irrelevant. In this case the 
    `coeffs` parameter passed to the function would be:

        np.array([1, 0, 1, 1, 0.25])
        
    In this way the contribution of that parameter to the fitness will
    always be 0. Note that you may also want to set the corresponding 
    exponent to 0 as well. This may lead to a faster calculation. Notice
    that the carrot term has the coeffiecient set to 0.25. This gives
    it the same weighing as the other terms in the penalty term. The 
    difference is due to the fact that the penality term's exponents are
    summed first and then used in 1/x, while the carrot term is not 
    summed or passed through an inverse function.
  
    Parameters
    ----------
    macro_mol : Cage
        The cage whose fitness is to be calculated.
        
    target_cavity : float
        The desried size of the cage's pore.
        
    macromodel_path : str
        The Schrodinger directory path.

    target_window : float (default = None)
        The desired radius of the largest window of the cage. If 
        ``None`` then `target_cavity` is used.
        
    coeffs : numpy.array (default = None)
        An array holding the coeffients A to N in equation (2).
        
    exponents : numpy.array (default = None)
        An array holding the exponents a to n in equation (2).
        
    means : numpy.array (default = None)
        A numpy array holding the mean values of var1 to varX over the
        population. Used in the scaling procedure decribed in 
        ``calc_fitness``.
    
    Returns
    -------
    The fitness function will be called on each cage twice. Once to get
    the unscaled values of all the var parameters. This will return an 
    array. The second time the average of the unscaled values is used 
    for scaling. The scaled values are then used to calculate the final 
    fitness as a float. This is returned after the second call. More
    details in ``calc_fitness``.
    
    float
        The fitness of `macro_mol`.
        
    numpy.array
        A numpy array holding unsacled values of var1 to varX. This is 
        returned during the scaling procedure described in 
        ``calc_fitness``.

    Raises
    ------
    ValueError
        When the average of the negavite bond formation energy is 
        positive.

    """

    # Go into this ``if`` block if the `means` parameter is provided.
    # This means that the unnormalized fitness paramters have already 
    # been found and their mean taken. Now the scaled fitness paramters
    # must be found and combined into a single final, fitness value.
    if means is not None:        
        # If there was some issue with calculating the unscaled fitness
        # parameters give a low fitness.        
        if macro_mol.unscaled_fitness_vars is None:
            return 1e-4
        
        # Set the default coeffient values.
        if coeffs is None:
            coeffs = np.array([1,1,1,1,0.2])
            
        # Set the default exponent values.
        if exponents is None:
            exponents = np.array([1,1,1,1,1])  
        
        # Make sure you are not dividing by 0.
        for i, x in enumerate(means):
            if x == 0:
                means[i] = 1
        
        # The normalized fitness paramter is found by dividing the value
        # of that parameter in that individual by the mean value within
        # the population.
        scaled = np.divide(macro_mol.unscaled_fitness_vars, means)
        
        fitness_vars = np.power(scaled, exponents)
        fitness_vars = np.multiply(fitness_vars, coeffs)    
        penalty_term = np.sum(fitness_vars[:-1])
        penalty_term =  np.divide(1,penalty_term)
        if penalty_term > 1e101:
            penalty_term = 1e101
        
        # Carrots and sticks, where the previous fitness parameters were
        # the sticks.
        carrot_term = fitness_vars[-1]
        
        return penalty_term + carrot_term

    # If unscaled fitness paramters need to be calculated, the following
    # code is executed.

    # If pyWindow returned ``None`` some error occured. Set the various
    # attributes and return value to ``None`` as a result. 
    if macro_mol.topology.windows is None:
        macro_mol.unscaled_fitness_vars = None
        return
    
    # If the unsacled fitness paramters have already be calculted,
    # return them. They're unscaled so they will not have changed.
    if hasattr(macro_mol, 'unscaled_fitness_vars'):
        return macro_mol.unscaled_fitness_vars

    # Calculate the difference between the cavity size of the cage and
    # the desired cavity size.
    cavity_diff = abs(target_cavity - macro_mol.topology.cavity_size())
    # Calculate the window area required to fit a molecule of the target
    # size through.
    if target_window is None:
        target_window = target_cavity
    # The point is to allow only molecules of the target size to
    # diffuse through the cage, no bigger molecules. To do this the
    # biggest window of the cage must be found. The difference between
    # this window and the target window size is then found.
    window_diff = abs(target_window - max(macro_mol.topology.windows)) 
    # Check the assymetry of the cage.
    asymmetry = macro_mol.topology.window_difference()
    # Check the formation energy of the cage. Treat the positive and
    # negative cases separately.
    energy_per_bond = macro_mol.formation_energy(macromodel_path)
    if energy_per_bond < 0:
        neg_eng_per_bond = energy_per_bond
        pos_eng_per_bond = 0
    else:
        neg_eng_per_bond = 0
        pos_eng_per_bond = energy_per_bond

    unscaled =  np.array([
                     cavity_diff, 
                     window_diff,                                                          
                     asymmetry,
                     pos_eng_per_bond,
                     neg_eng_per_bond
                     ])
    macro_mol.unscaled_fitness_vars = unscaled
    return unscaled
    
def cage_target(cage, target_mol_file, target_size, *, macromodel_path, 
                rotate=False, min_window_size=0):
    """
    Calculates the fitness of a cage / target complex.
    
    Depending of `rotate` a different number of cage / target 
    complexes will be generated. When `rotate` is ``True``, the 
    target molecule is rotated along the x, y and z axes and each
    rotation forms a new complex. The lowest energy complex is used
    for the fitness calculation. When `rotate` is ``False`` not 
    rotation takes place.
    
    To see which rotations take place see the documentation of the
    `generate_complexes` method.
    
    Parameters
    ----------
    cage : Cage
        The cage which is to have its fitness calculated,

    target_mol_file : str
        The full path of the .mol file hodling the target molecule
        placed inside the cage.
        
    target_size : float
        The minimum size which the cage cavity needs to be in order to
        encapsulate the target.
        
    min_window_size : float (default = 0)
        The smallest windows size allowing the target to enter the cage.
        Default is 0, which implies that there is no minimum. This can
        occur when the target acts a template for cage assembly.

    rotate : bool (default = False)
        When ``True`` the target molecule will be rotated inside the
        cavity of the cage. When ``False`` only the orientation
        within the .mol file is used.
        
    macromodel_path : str (keyword-only)
        The Schrodinger directory path.
        
    Returns
    -------
    float
        The fitness value of `cage`.
    
    """
    
    # If the cage already has a fitness value, don't run the
    # calculation again.
    if cage.fitness:
        print('Skipping {0}'.format(cage.prist_mol_file))
        return cage.fitness
    
    # The first time running the fitness function create an instance
    # of the target molecule as a ``StructUnit``. Due to caching,
    # running the initialization again on later attempts will not 
    # re-initialize.
    target = StructUnit(target_mol_file, minimal=True)

    optimization.macromodel_opt(target, no_fix=True, 
                                macromodel_path=macromodel_path)

    # This function creates a new molecule holding both the target
    # and the cage centered at the origin. It then calculates the 
    # energy of this complex and compares it to the energies of the
    # molecules when separate. The more stable the complex relative
    # to the individuals the higher the fitness.
    
    # Create rdkit instances of the target in the cage for each
    # rotation.        
    rdkit_complexes = list(_generate_complexes(cage, target, rotate))
    
    # Place the rdkit complexes into a new .mol file and use that 
    # to make a new ``StructUnit`` instance of the complex.
    # ``StructUnit`` is the class of choice here because it can be
    # initialized from a .mol file. ``MacroMolecule`` requires
    # things like topology and building blocks for initialization.
    macromol_complexes = []        
    for i, complex_ in enumerate(rdkit_complexes):
        # First the data is loaded into a ``MacroMolecule`` instance
        # as this is the class which is able to write rdkit
        # instances to .mol files. Note that this ``MacroMolecule``
        # instance is just a dummy and only holds the bare minimum
        # information required to write the complex to a .mol file.
        mm_complex = MacroMolecule.__new__(MacroMolecule)
        mm_complex.prist_mol = complex_
        mm_complex.prist_mol_file = cage.prist_mol_file.replace(
                            '.mol', '_COMPLEX_{0}.mol'.format(i))
        mm_complex.write_mol_file('prist')
        
        # Once the .mol file is written load it into a 
        # ``StructUnit`` instance.
        macromol_complex = StructUnit(mm_complex.prist_mol_file, 
                                      minimal=True)
        optimization.macromodel_opt(macromol_complex, no_fix=True,
                       macromodel_path=macromodel_path)
        macromol_complexes.append(macromol_complex)
    
    # Calculate the energy of the complex and compare to the
    # individual energies. If more than complex was made, use the
    # most stable version.
    energy_separate = cage.energy + target.energy
    energy_diff =  min(macromol_complex.energy - energy_separate for 
                            macromol_complex in macromol_complexes)
    
                       
    raw_fitness = np.exp(energy_diff*1e-5) + 1
    if raw_fitness > 1e10:
        raw_fitness = 1e10
        
    return raw_fitness
   
def _generate_complexes(cage, target, rotate):
    """
    Yields rdkit instances of cage / target complexes.
    
    Parameters
    ----------
    cage : Cage
        The cage used to form the complex.
        
    target : StructUnit
        The target used to form the complex.
        
    rotate : bool
        When ``True`` the target molecule will undergo rotations
        within the cage cavity and a complex will be yielded for 
        each configuration.
        
    Yields
    ------
    rdkit.Chem.rdchem.Mol
        An rdkit instance holding the cage / target complex. 
    
    """
    
    # Define the rotations which are to be used on the target.
    if rotate:        
        rotations = [0, np.pi/2, np.pi, 3*np.pi/2]
    else:
        rotations = [0]

    # First place both the target and cage at the origin.
    cage.set_position('prist', [0,0,0])
    target.set_position('prist', [0,0,0])
    
    # Get the position matrix of the target molecule.        
    og_pos_mat = target.position_matrix('prist')
    
    # Carry out every rotation and yield a complex for each case.
    for rot1, rot2, rot3 in it.combinations_with_replacement(
                                                    rotations, 3):
        rot_target = copy.deepcopy(target)
        rot_mat1 = rotation_matrix_arbitrary_axis(rot1, [1,0,0])
        rot_mat2 = rotation_matrix_arbitrary_axis(rot2, [0,1,0])
        rot_mat3 = rotation_matrix_arbitrary_axis(rot3, [0,0,1])
        
        new_pos_mat = np.dot(rot_mat1, og_pos_mat)
        new_pos_mat = np.dot(rot_mat2, new_pos_mat)
        new_pos_mat = np.dot(rot_mat3, new_pos_mat)
        
        rot_target.set_position_from_matrix('prist', new_pos_mat)
        
        yield chem.CombineMols(cage.prist_mol, rot_target.prist_mol)
    


    
    
        
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
