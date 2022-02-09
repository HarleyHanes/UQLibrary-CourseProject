# -*- coding: utf-8 -*-
"""
Created on Tue Jan 18 14:03:35 2022

@author: USER
"""

#3rd party Modules
import numpy as np
#import sys
#import warnings
#import matplotlib.pyplot as plt
#import scipy.integrate as integrate
#from tabulate import tabulate                       #Used for printing tables to terminal
#import sobol                                        #Used for generating sobol sequences
from SALib.sample.sobol_sequence import sample as sobol_sample
import scipy.stats as sct

class GsaOptions:
    def __init__(self, run = True, run_sobol=True, run_morris=True, n_samp_sobol=100000, \
                 n_samp_morris=4, l_morris=3):
        self.run = run
        if self.run == False:
            self.run_sobol = False
            self.run_morris = False
        else:
            self.run_sobol=run_sobol                            #Whether to run Sobol (True or False)
            self.run_morris=run_morris                          #Whether to run Morris (True or False)
        self.n_samp_sobol = n_samp_sobol                      #Number of samples to be generated for GSA
        self.n_samp_morris = n_samp_morris
        self.l_morris=l_morris
        pass

class GsaResults:
    #
    def __init__(self,sobol_base=np.nan, sobol_tot=np.nan, f_a=np.nan, f_b=np.nan, f_d=np.nan, f_ab=np.nan, \
                 samp_d=np.nan, morris_variance=np.nan, morris_mean_abs=np.nan, morris_mean=np.nan):
        self.sobol_base=sobol_base
        self.sobol_tot=sobol_tot
        self.f_a=f_a
        self.f_b=f_b
        self.f_d=f_d
        self.f_ab=f_ab
        self.samp_d=samp_d
        self.morris_mean_abs=morris_mean_abs
        self.morris_mean = morris_mean
        self.morris_variance=morris_variance
    pass



##--------------------------------------GSA-----------------------------------------------------
def run_gsa(model, gsa_options):
    """Implements global sensitivity analysis using Morris or Sobol analysis.
    
    Parameters
    ----------
    model : Model
        Contaings simulation information.
    gsa_options : GSAOptions
        Contains run settings
        
    Returns
    -------
    GsaResults 
        Holds all run results
    """
    #GSA implements the following local sensitivity analysis methods on "model" object
        # 1) Gets sampling distribution (used only for internal calculations)
        # 2) Calculates Sobol Indices
        # 3) Performs Morris Screenings (not yet implemented)
        # 4) Produces histogram plots for QOI values (not yet implemented)
    # Required Inputs: Object of class "model" and object of class "options"
    # Outputs: Object of class gsa with fisher and sobol elements

    #Get Parameter Distributions
    model=get_samp_dist(model, gsa_options)
    gsa_results = GsaResults()
    #Morris Screening
    if gsa_options.run_morris:
        #Set non-biased perturbation distance for even l
        #Source: Smith, R. 2011. Uncertainty Quanitification. p.333
        pert_distance = gsa_options.l_morris/ (2*(gsa_options.l_morris-1))
        
        morris_samp = get_morris_poi_sample(model.dist, gsa_options.n_samp_morris,\
                                            model.n_poi, pert_distance)
            
        morris_mean_abs, morris_mean, morris_variance = calculate_morris(\
                                             model.eval_fcn, morris_samp, \
                                             pert_distance)
        gsa_results.morris_mean_abs=morris_mean_abs
        gsa_results.morris_mean = morris_mean
        gsa_results.morris_variance=morris_variance

    #Sobol Analysis
    if gsa_options.run_sobol:
        #Make Distribution Samples and Calculate model results
        [f_a, f_b, f_ab, f_d, samp_d] = get_sobol_sample(model, gsa_options)
        #Calculate Sobol Indices
        [sobol_base, sobol_tot]=calculate_sobol(f_a, f_b, f_ab, f_d)
        gsa_results.f_d=f_d
        gsa_results.f_a=f_a
        gsa_results.f_b=f_b
        gsa_results.f_ab=f_ab
        gsa_results.samp_d=samp_d
        gsa_results.sobol_base=sobol_base
        gsa_results.sobol_tot=sobol_tot
        
    return gsa_results


###----------------------------------------------------------------------------------------------
###-------------------------------------Support Functions----------------------------------------
###----------------------------------------------------------------------------------------------


def get_sobol_sample(model,gsa_options):
    """Constructs and evaluates sobol samples using predefined sampling distributions.
        Currently only function for uniform or saltelli normal
    
    Parameters
    ----------
    model : Model
        Contaings simulation information.
    gsa_options : GSAOptions
        Contains run settings
        
    Returns
    -------
    np.ndarray
        n_samp_sobol x n_qoi array of evaluations of Sobol sample part a
    np.ndarray
        n_samp_sobol x n_qoi array of evaluations of Sobol sample part b
    np.ndarray
        n_samp_sobol x n_qoi array x n_poi array of evaluations of mixed Sobol sample ab
    np.ndarray
        2*n_samp_sobol x n_qoi array of concatenated evaluations of part a and b
    np.ndarray
        2*n_samp_sobol x n_poi array of concatenated POI samples of part a and b
    """
    n_samp_sobol = gsa_options.n_samp_sobol
    # Make 2 POI sample matrices with n_samp_sobol samples each
    if model.dist.lower()=='uniform' or model.dist.lower()=='saltellinormal':
        (samp_a, samp_b)=model.sample(n_samp_sobol);                                     #Get both A and B samples so no repeated values
    else:
        #-------Error, need to switch these samplings to the join Saltelli-------------
        samp_a = model.sample(n_samp_sobol)
        samp_b = model.sample(n_samp_sobol)
    # Calculate matrices of QOI values for each POI sample matrix
    f_a = model.eval_fcn(samp_a).reshape([n_samp_sobol, model.n_qoi])  # n_samp_sobol x nQOI out matrix from A
    f_b = model.eval_fcn(samp_b).reshape([n_samp_sobol, model.n_qoi])  # n_samp_sobol x nQOI out matrix from B
    # Stack the output matrices into a single matrix
    f_d = np.concatenate((f_a.copy(), f_b.copy()), axis=0)

    # Initialize combined QOI sample matrices
    if model.n_qoi == 1:
        f_ab = np.empty([n_samp_sobol, model.n_poi])
    else:
        f_ab = np.empty([n_samp_sobol, model.n_poi, model.n_qoi])
    for i_param in range(0, model.n_poi):
        # Define sampC to be A with the ith parameter in B
        samp_ab = samp_a.copy()
        samp_ab[:, i_param] = samp_b[:, i_param].copy()
        if model.n_qoi == 1:
            f_ab[:, i_param] = model.eval_fcn(samp_ab)
        else:
            f_ab[:, i_param, :] = model.eval_fcn(samp_ab)  # n_samp_sobol x nPOI x nQOI tensor
        del samp_ab
    return f_a, f_b, f_ab, f_d, np.concatenate((samp_a.copy(), samp_b.copy()), axis=0)

def calculate_sobol(f_a, f_b, f_ab, f_d):
    """Calculates 1st order and total sobol indices using Saltelli approximation formula.
    
    Parameters
    ----------
    f_a : np.ndarray
        n_samp_sobol x n_qoi array of evaluations of Sobol sample part a
    f_b : np.ndarray
        n_samp_sobol x n_qoi array of evaluations of Sobol sample part b
    f_ab : np.ndarray
        n_samp_sobol x n_qoi array x n_poi array of evaluations of mixed Sobol sample ab
    f_d : np.ndarray
        2*n_samp_sobol x n_qoi array of concatenated evaluations of part a and b
    
        
    Returns
    -------
    np.ndarray
        n_qoi x n_poi array of 1st order Sobol indices
    np.ndarray
        n_qoi x n_poi array of total Sobol indices
    """
    #Calculates calculates sobol indices using satelli approximation method
    #Inputs: model object (with eval_fcn, sample, and nParams)
    #        sobolOptions object
    #Determing number of samples, QOIs, and POIs based on inputs
    if f_ab.ndim==1:
        n_qoi=1
        n_poi=1
    elif f_ab.ndim==2:
        n_qoi=1
        n_poi=f_ab.shape[1]
    elif f_ab.ndim==3:
        n_poi=f_ab.shape[1]
        n_qoi=f_ab.shape[2]
    else:
        raise(Exception('f_ab has greater than 3 dimensions, make sure f_ab is' \
                        'the squeezed form of n_samp_sobol x nPOI x nQOI'))
    #QOI variance
    fDvar=np.var(f_d, axis=0)

    sobol_base=np.empty((n_qoi, n_poi))
    sobol_tot=np.empty((n_qoi, n_poi))
    if n_qoi==1:
        #Calculate 1st order parameter effects
        sobol_base=np.mean(f_b*(f_ab-f_a), axis=0)/(fDvar)

        #Caclulate 2nd order parameter effects
        sobol_tot=np.mean((f_a-f_ab)**2, axis=0)/(2*fDvar)

    else:
        for iQOI in range(0,n_qoi):
            #Calculate 1st order parameter effects
            sobol_base[iQOI,:]=np.mean(f_b[:,[iQOI]]*(f_ab[:,:,iQOI]-f_a[:,[iQOI]]),axis=0)/fDvar[iQOI]
            #Caclulate 2nd order parameter effects
            sobol_tot[iQOI,:]= np.mean((f_a[:,[iQOI]]-f_ab[:,:,iQOI])**2,axis=0)/(2*fDvar[iQOI])


    return sobol_base, sobol_tot
#==============================================================================
#----------------------------------Morris Sampling-----------------------------
#==============================================================================


##--------------------------------calculate_morris-----------------------------
def calculate_morris(eval_fcn, morris_samp, pert_distance):
    """Calculates morris samples using information from Model and GsaOptions objects.
    
    Parameters
    ----------
    model : Model
        Contaings simulation information.
    gsa_options : GSAOptions
        Contains run settings
        
    Returns
    -------
    np.ndarray
        n_qoi x n_poi array of morris sensitivity mean indices
    np.ndarray
        n_qoi x n_poi array of morris sensitivity variance indices
    """
    #Evaluate Sample
    f_eval_compact = eval_fcn(morris_samp)
    
    #Compute # of pois, qois and samples to ensure consitency
    n_poi = morris_samp.shape[1]
    n_samp = morris_samp.shape[0]/(n_poi+1)
    n_qoi = f_eval_compact.shape[1]
    
    #Seperate each parameter search for ease of computation
    f_eval_seperated = np.empty((n_samp, n_poi+1, n_qoi))
    for i_samp in range(n_samp):
        f_eval_seperated[n_samp,:,:] = f_eval_compact[i_samp*(n_poi+1):(i_samp+1)*(n_poi+1),:]
        
    deriv_approx = np.empty((n_samp, n_poi, n_qoi))  # n_samp x n_poi x n_qoi
    
    #Apply finite difference formula 
    #Source: Smith, R. 2011, Uncertainty Quanitification. p.333
    for i_poi in range(n_poi):
        deriv_approx[:,i_poi,:] = f_eval_seperated[:,i_poi+1,:] - f_eval_seperated[:,i_poi,:]
        
    #Apply Morris Index formula
    #Source: Smith, R. 2011, Uncertainty Quanitification. p.332
    morris_mean_abs = np.mean(np.abs(deriv_approx),axis = 0) # n_poi x n_qoi
    morris_mean = np.mean(deriv_approx, axis = 0)
    morris_variance=np.var(deriv_approx, axis=0) # n_poi x n_qoi

    return morris_mean_abs, morris_mean, morris_variance

##---------------------------get_morris_poi_sample-----------------------------

def get_morris_poi_sample(param_dist, n_samp, n_poi, pert_distance, random = True):
    #Use sobol distributions for low discrepancy
    #Generate n_samp_morris samples
    random_samp =  param_dist(n_samp)
    #Define Sampling matrices that are constant
    J=np.ones((n_poi+1,n_poi))
    B = (np.tril(np.ones(J.shape), -1))
    morris_samp = np.empty((n_samp*(n_poi+1), n_poi))
    for i_samp in range(n_samp):
        jTheta=random_samp[i_samp,]*J
        #Calculate Morris Sample matrix
        #Source: Smith, R. 2011. Uncertainty Quantification. p.334
        if random == True:  
            #Define Random Sampling matrices
            D=np.diag(np.random.choice(np.array([1,-1]), size=(n_poi,)))
            P=np.identity(n_poi)
            np.random.shuffle(P)
            samp_mat = np.matmul(jTheta+pert_distance/2*(np.matmul((2*B-J),D)+J),P)
        elif random == False:
            #Define non-random Sampling matrices
            D=np.diag(np.random.choice(np.array([1,1]), size=(n_poi,)))
            P=np.identity(n_poi)
            np.random.shuffle(P)
            # Only use non-random formulations for testing matrix generation
            samp_mat = jTheta+pert_distance/2*(np.matmul((2*B-J),D)+J)
        #Stack each grid seach so that a single eval_fcn call is required
        morris_samp[i_samp*(n_poi+1):(i_samp+1)*(n_poi+1),:] = samp_mat
    return morris_samp
        

##--------------------------------------GetSampDist----------------------------------------------------
def get_samp_dist(model, gsa_options):
    """Adds sampling function sample to model for drawing of low-discrepency
        from given distribution type.
    
    Parameters
    ----------
    model : Model
        Contaings simulation information.
    gsa_options : GSAOptions
        Contains run settings
        
    Returns
    -------
    Model
        model object with added sample function
    """
    # Determine Sample Function- Currently only 1 distribution type can be defined for all parameters
    if model.dist.lower() == 'normal':  # Normal Distribution
        sample = lambda n_samp_sobol: np.random.randn(n_samp_sobol,model.n_poi)*np.sqrt(model.dist_param[[1], :]) + model.dist_param[[0], :]
    elif model.dist.lower() == 'saltellinormal':
        sample = lambda n_samp_sobol: saltelli_normal(n_samp_sobol, model.dist_param)
    elif model.dist.lower() == 'uniform':  # uniform distribution
        # doubleParms=np.concatenate(model.dist_param, model.dist_param, axis=1)
        sample = lambda n_samp_sobol: saltelli_sample(n_samp_sobol,model.dist_param)
    elif model.dist.lower() == 'exponential': # exponential distribution
        sample = lambda n_samp_sobol: np.random.exponential(model.dist_param,size=(n_samp_sobol,model.n_poi))
    elif model.dist.lower() == 'beta': # beta distribution
        sample = lambda n_samp_sobol:np.random.beta(model.dist_param[[0],:], model.dist_param[[1],:],\
                                               size=(n_samp_sobol,model.n_poi))
    elif model.dist.lower() == 'InverseCDF': #Arbitrary distribution given by inverse cdf
        sample = lambda n_samp_sobol: gsa_options.fcn_inverse_cdf(np.random.rand(n_samp_sobol,model.n_poi))
    else:
        raise Exception("Invalid value for gsa_options.dist. Supported distributions are normal, uniform, exponential, beta, \
        and InverseCDF")  # Raise Exception if invalide distribution is entered
    model.sample=sample
    return model



def saltelli_sample(n_samp_sobol,dist_param):
    """Constructs a uniform low discrepency saltelli sample for use in Sobol
        index approximation
    
    Parameters
    ----------
    n_samp_sobol : int
        Number of samples to take
    dist_param : np.ndarray
        2 x n_poi array of min and max sampling bounds for each parameter
        
    Returns
    -------
    np.ndarray
        POI sample part a
    np.ndarray
        POI sample part b
    """
    n_poi=dist_param.shape[1]
    #base_sample=sobol.sample(dimension=n_poi*2, n_points=n_samp_sobol, skip=1099)
    base_sample=sobol_sample(n_samp_sobol,n_poi*2)
    base_a=base_sample[:,:n_poi]
    base_b=base_sample[:,n_poi:2*n_poi]
    samp_a=dist_param[[0],:]+(dist_param[[1],:]-dist_param[[0],:])*base_a
    samp_b=dist_param[[0],:]+(dist_param[[1],:]-dist_param[[0],:])*base_b
    return (samp_a, samp_b)

def saltelli_normal(n_samp_sobol, dist_param):
    """Constructs a normal low discrepency saltelli sample for use in Sobol
        index approximation
    
    Parameters
    ----------
    n_samp_sobol : int
        Number of samples to take
    dist_param : np.ndarray
        2 x n_poi array of mean and variance for each parameter
        
    Returns
    -------
    np.ndarray
        POI sample part a
    np.ndarray
        POI sample part b
    """
    n_poi=dist_param.shape[1]
    #base_sample=sobol.sample(dimension=n_poi*2, n_points=n_samp_sobol, skip=1099)
    base_sample=sobol_sample(n_samp_sobol,n_poi*2)
    base_a=base_sample[:,:n_poi]
    base_b=base_sample[:,n_poi:2*n_poi]
    transformA=sct.norm.ppf(base_a)
    transformB=sct.norm.ppf(base_b)
    samp_a=transformA*np.sqrt(dist_param[[1], :]) + dist_param[[0], :]
    samp_b=transformB*np.sqrt(dist_param[[1], :]) + dist_param[[0], :]
    return (samp_a, samp_b)
