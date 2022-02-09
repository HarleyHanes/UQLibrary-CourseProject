#UQtoolbox
#Module for calculating local sensitivity indices, parameter correlation, and Sobol indices for an arbitrary model
#Authors: Harley Hanes, NCSU, hhanes@ncsu.edu
#Required Modules: numpy, seaborne
#Functions: LSA->GetJacobian
#           GSA->ParamSample, PlotGSA, GetSobol

#3rd party Modules
import numpy as np
import sys
import warnings
import matplotlib.pyplot as plt
import scipy.integrate as integrate
from tabulate import tabulate                       #Used for printing tables to terminal
#import sobol                                        #Used for generating sobol sequences
import SALib.sample.saltelli as sobol
import scipy.stats as sct

#Package Modules
import lsa
import gsa
#import seaborne as seaborne
###----------------------------------------------------------------------------------------------
###-------------------------------------Class Definitions----------------------------------------
###----------------------------------------------------------------------------------------------

##--------------------------------------uqOptions--------------------------------------------------
#Define class "uqOptions", this will be the class used to collect algorithm options for functions
#   -Subclasses: lsaOptions, plotOptions, gsaOptions
#--------------------------------------lsaOptions------------------------------------------------

#--------------------------------------gsaOptions------------------------------------------------

#--------------------------------------plotOptions------------------------------------------------
class PlotOptions:
    def __init__(self,run=True,n_points=400,path=False):
        self.run=run
        self.n_points=n_points
        self.path=path
        pass
#--------------------------------------uqOptions------------------------------------------------
#   Class holding the above options subclasses
class Options:
    def __init__(self,lsa=lsa.LsaOptions(),plot=PlotOptions(),gsa=gsa.GsaOptions(), \
                 display=True, save=False, path='..'):
        self.lsa=lsa
        self.plot=plot
        self.gsa=gsa
        self.display=display                       #Whether to print results to terminal
        self.save=save                             #Whether to save results to files
        self.path=path                             #Where to save files
        if self.save and not self.path:
            warnings.warn("Save marked as true but no path given, saving files to current folder.")
            path=''
    pass

##-------------------------------------model------------------------------------------------------
#Define class "model", this will be the class used to collect input information for all functions
class Model:
    #Model sets should be initialized with base parameter settings, covariance Matrix, and eval function that
    #   takes in a vector of POIs and outputs a vector of QOIs
    def __init__(self,base_poi=np.empty(0), name_poi = np.empty(0), \
                 name_qoi= np. empty(0), cov=np.empty(0), \
                 eval_fcn=np.empty(0), dist_type='uniform', dist_param="auto"):
        #------------------------base_poi, n_poi, name_poi---------------------
        #Assign base_poi and n_poi
        if not isinstance(base_poi,np.ndarray):                    #Confirm that base_poi is a numpy array
            raise Exception("model.base_poi is not a numpy array")
        if np.ndim(base_poi)>1:                                    #Check to see if base_poi is a vector
            base_poi=np.squeeze(base_poi)                     #Make a vector if an array with 1 dim greater than 1
            if np.ndim(base_poi)!=1:                               #Issue an error if base_poi is a matrix or tensor
                raise Exception("Error! More than one dimension of size 1 detected for model.base_poi, model.base_poi must be dimension 1")
            else:                                                       #Issue a warning if dimensions were squeezed out of base POIs
                warnings.warn("model.base_poi was reduced a dimension 1 array. No entries were deleted.")
        self.base_poi=base_poi
        del base_poi
        self.n_poi=self.base_poi.size
        
        #Assign name_poi----------------UNFINISHED VALUE CHECKING
        #Check name_poi is string
        if type(name_poi)==np.ndarray:
            #Check data type
            if name_poi.size!= self.n_poi:
                raise Exception("Incorrect number of entries in name_poi")
            self.name_poi=name_poi
        elif type(name_poi)==list:
            #Check data type
            if len(name_poi)!= self.n_poi:
                raise Exception("Incorrect number of entries in name_poi")
            self.name_poi=np.array(name_poi)
        elif type(name_poi)==str and name_poi.lower()!="auto":
            if self.n_poi!=1:
                raise Exception("Only one qoi name entered for >1 pois")
            else :
                self.name_qoi = name_qoi
        else :
            POInumbers=np.arange(0,self.n_poi)
            name_poi=np.char.add('POI',POInumbers.astype('U'))
            if name_poi.lower()!= "auto":
                warnings.warn("Unrecognized name_poi entry, using automatic values")
        if (name_poi.size != self.n_poi) & (name_poi.size !=0):   #Check that correct size if given
            warnings.warn("name_poi entered but the number of names does not match the number of POIs. Ignoring names.")
            name_poi=np.empty(0)
        if name_poi.size==0:                                           #If not given or incorrect size, number POIs
            POInumbers=np.arange(0,self.n_poi)
            name_poi=np.char.add('POI',POInumbers.astype('U'))
            
        #-----------------eval_fcn, base_qoi, n_qoi, name_qoi------------------
        #Assign evaluation function and compute base_qoi
        self.eval_fcn=eval_fcn
        del eval_fcn
        self.base_qoi=self.eval_fcn(self.base_poi)
        if not isinstance(self.base_qoi,np.ndarray):                    #Confirm that base_qoi is a numpy array
            warnings.warn("model.base_qoi is not a numpy array")
        self.n_qoi=len(self.base_qoi)
        
        #Assign name_qoi----------------UNFINISHED VALUE CHECKING
        #Check name_qoi is string
        if type(name_qoi)==np.ndarray:
            #Check data type
            if name_qoi.size!= self.n_qoi:
                raise Exception("Incorrect number of entries in name_qoi")
            self.name_qoi = name_qoi
        elif type(name_qoi)==list:
            #Check data type
            if len(name_qoi)!= self.n_qoi:
                raise Exception("Incorrect number of entries in name_qoi")
            self.name_qoi=np.array(name_qoi)
        elif type(name_qoi)==str and name_qoi.lower()!="auto":
            if self.n_qoi!=1:
                raise Exception("Only one qoi name entered for >1 qois")
            else: 
                self.name_qoi = name_qoi
        else :
            QOInumbers=np.arange(0,self.n_qoi)
            name_qoi=np.char.add('POI',QOInumbers.astype('U'))
            if name_poi.lower()!= "auto":
                warnings.warn("Unrecognized name_qoi entry, using automatic values")
        self.name_qoi = name_qoi
        if (self.name_qoi.size !=self.n_qoi) & (self.name_qoi.size !=0):    #Check names if given match number of QOIs
            warnings.warn("name_qoi entered but the number of names does not match the number of QOIs. Ignoring names.")
            self.name_qoi = np.empty(0)
        if self.name_qoi.size==0:                                 #If not given or incorrect size, number QOIs
            QOInumbers = np.arange(0, self.n_qoi)
            self.name_qoi = np.char.add('QOI', QOInumbers.astype('U'))
            
            
            
            
        #------------------------------covariance matrix-----------------------
        self.cov=cov
        if self.cov.size!=0 and np.shape(self.cov)!=(self.n_poi,self.n_poi): #Check correct sizing
            raise Exception("Error! model.cov is not an nPOI x nPOI array")
            
        #--------------------------------dist_type-----------------------------
        #Only allow distributions that are currently fully implemented
        valid_distribution =np.array(["uniform", "saltelli uniform", "normal", \
                                      "saltelli normal"])
        # valid_distribution =np.array(["uniform", "normal", "exponential", \
        #                           "saltelli normal", "beta", "InverseCDF"])
        #If distribution type is valid, save its value
        if np.all(dist_type!= valid_distribution):
            raise Exception(str(dist_type) + " is an invalid distribution. Valid" +\
                            " distributions are" + str(valid_distribution))
        else:
            self.dist_type=dist_type
            del dist_type
                
        #--------------------------------dist_param----------------------------
        # Apply automatic distribution parameter settings
        if str(dist_param).lower() == 'auto':
            if (self.dist_type == "uniform" or self.dist_type == "saltelli uniform"):
                self.dist_param=[[.8],[1.2]]*np.ones((2,self.n_poi))*self.base_poi
                del dist_param
            elif (self.dist_type == "normal" or self.dist_type == "saltelli normal"):
                if cov.size()==0:
                    self.dist_param=[[1],[.2]]*np.ones((2,self.n_poi))*self.base_poi
                    del dist_param
        # Apply manual distribution settings
        elif type(dist_param) == np.ndarray:
            #Check dimensions of numpy array are correct
            if dist_param.shape[1] == self.n_poi:
                # Correct number of parameters for each distribution
                if (self.dist_type == "uniform" or self.dist_type == "saltelli uniform")\
                    and dist_param.shape[0]!=2:
                    raise Exception("2 parameters per POI required for uniform")
                elif (self.dist_type == "normal" or self.dist_type == "saltelli normal")\
                    and dist_param.shape[0]!=2:
                    raise Exception("2 parameters per POI required for normal")
                # Assign dist_param if conditions met
                else :
                    self.dist_param=dist_param
                    del dist_param
            else:
                raise Exception("Incorrect shape of dist_param. Given shape: "\
                                + dist_param.shape + ", desired shape: ... x n_poi") 
        elif dist_param.lower() == "cov":
            if np.any(self.dist_type.lower()==["normal", "saltelli normal"]):
                self.dist_param=[self.base_poi, np.diag(self.cov,k=0)]   
                del dist_param 
            else :
                raise Exception("Covariance based sampling only implemented for"\
                                +"normal or saltelli normal distributions")
        else:
            raise Exception("Incorrect data-type for dist_param, use ndarray, 'auto', or 'cov'")
            
        #Construct Distribution function
        self.sample_fcn = gsa.get_samp_dist(self.dist_type, self.dist_param, self.n_poi)
    
    pass
    def copy(self):
        return Model(base_poi=self.base_poi, name_poi = self.name_poi, name_qoi= self.name_qoi, cov=self.cov, \
                 eval_fcn=self.eval_fcn, dist_type=self.dist_type,dist_param=self.dist_param)

##------------------------------------results-----------------------------------------------------
# Define class "results" which holds a gsaResults object and lsaResults object

class Results:
    def __init__(self,lsa=lsa.LsaResults(), gsa=gsa.GsaResults()):
        self.lsa=lsa
        self.gsa=gsa
    pass


###----------------------------------------------------------------------------------------------
###-------------------------------------Main Functions----------------------------------------
###----------------------------------------------------------------------------------------------
#   The following functions are the primary functions for running the package. RunUQ runs both local sensitivity
#   analysis and global sensitivity analysis while printing to command window summary statistics. However, local
#   sensitivity analysis and global sensitivity analysis can be run independently with LSA and GSA respectively

##--------------------------------------RunUQ-----------------------------------------------------
def run_uq(model, options):
    """Runs both the local and global sensitivity, and result printing, saving, and plotting.
    
    Parameters
    ----------
    model : Model
        Object of class Model holding run information.
    options : Options
        Object of class Options holding run settings.
        
    Returns
    -------
    Results 
        Object of class Results holding all run results.
    """
    results = Results()
    #Run Local Sensitivity Analysis
    if options.lsa.run:
        results.lsa = lsa.run_lsa(model, options.lsa)

    #Run Global Sensitivity Analysis
    # if options.gsa.run:
        # if options.lsa.run:
        #     #Use a reduced model if it was caluclated
        #     results.gsa=GSA(results.lsa.reducedModel, options)
        # else:
    if options.gsa.run:
        results.gsa = gsa.run_gsa(model, options.gsa)

    #Print Results
    if options.display:
        print_results(results,model,options)                     #Print results to standard output path

    if options.save:
        original_stdout = sys.stdout                            #Save normal output path
        sys.stdout=open(options.path + 'Results.txt', 'a+')            #Change output path to results file
        print_results(results,model,options)                     #Print results to file
        sys.stdout=original_stdout                              #Revert normal output path

    #Plot Samples
    if options.gsa.run_sobol & options.gsa.run:
        plot_gsa(model, results.gsa.samp_d, results.gsa.f_d, options)

    return results



def print_results(results,model,options):
    """Prints Results object to console or document.
    
    Parameters
    ----------
    results : Results
        Object of class Model holding run information.
    model : Model
        Object of class Model holding run information.
    options : Options
        Object of class Options holding run settings.
    """
    # Print Results
    #Results Header
    print('Sensitivity results for nSampSobol=' + str(options.gsa.n_samp_sobol))
    #Local Sensitivity Analysis
    if options.lsa.run:
        print('\n Base POI Values')
        print(tabulate([model.base_poi], headers=model.name_poi))
        print('\n Base QOI Values')
        print(tabulate([model.base_qoi], headers=model.name_qoi))
        print('\n Sensitivity Indices')
        print(tabulate(np.concatenate((model.name_poi.reshape(model.n_poi,1),np.transpose(results.lsa.jac)),1),
              headers= np.append("",model.name_qoi)))
        print('\n Relative Sensitivity Indices')
        print(tabulate(np.concatenate((model.name_poi.reshape(model.n_poi,1),np.transpose(results.lsa.rsi)),1),
              headers= np.append("",model.name_qoi)))
        #print("Fisher Matrix: " + str(results.lsa.fisher))
        #Active Subsapce Analysis
        print('\n Active Supspace')
        print(results.lsa.active_set)
        print('\n Inactive Supspace')
        print(results.lsa.inactive_set)
    if options.gsa.run: 
        if options.gsa.run_sobol:
            if model.n_qoi==1:
                print('\n Sobol Indices for ' + model.name_qoi[0])
                print(tabulate(np.concatenate((model.name_poi.reshape(model.n_poi,1), results.gsa.sobol_base.reshape(model.n_poi,1), \
                                               results.gsa.sobol_tot.reshape(model.n_poi,1)), 1),
                               headers=["", "1st Order", "Total Sensitivity"]))
            else:
                for iQOI in range(0,model.n_qoi):
                    print('\n Sobol Indices for '+ model.name_qoi[iQOI])
                    print(tabulate(np.concatenate((model.name_poi.reshape(model.n_poi,1),results.gsa.sobol_base[[iQOI],:].reshape(model.n_poi,1), \
                        results.gsa.sobol_tot[[iQOI],:].reshape(model.n_poi,1)),1), headers = ["", "1st Order", "Total Sensitivity"]))
    
        if options.gsa.run_morris:
            if model.n_qoi==1:
                print('\n Morris Screening Results for' + model.name_qoi[0])
                print(tabulate(np.concatenate((model.name_poi.reshape(model.n_poi, 1), results.gsa.mu_star.reshape(model.n_poi, 1), \
                                               results.gsa.sigma2.reshape(model.n_poi, 1)), 1),
                    headers=["", "mu_star", "sigma2"]))
            else:
                print('\n Morris Screening Results for' + model.name_qoi[iQOI])
                print(tabulate(np.concatenate(
                    (model.name_poi.reshape(model.n_poi, 1), results.gsa.mu_star[[iQOI], :].reshape(model.n_poi, 1), \
                     results.gsa.sigma2[[iQOI], :].reshape(model.n_poi, 1)), 1),
                    headers=["", "mu_star", "sigma2"]))

###----------------------------------------------------------------------------------------------
###-------------------------------------Support Functions----------------------------------------
###----------------------------------------------------------------------------------------------


##--------------------------------------GetSobol------------------------------------------------------
# GSA Component Functions


#
#
def plot_gsa(model, sample_mat, eval_mat, options):
    """Plots Sobol Sampling results from gsa module.
    
    Parameters
    ----------
    model : Model
        Object of class Model holding run information.
    sample_mat: np.ndarray
        n_samp x n_poi array holding each parameter sample
    eval_mat : np.ndarray
        n_samp x n_qoi array holding each function evaluation
    options : Options
        Object of class Options holding run settings.
    """
    #Reduce Sample number
    #plotPoints=range(0,int(sample_mat.shape[0]), int(sample_mat.shape[0]/plotOptions.n_points))
    #Make the number of sample points to survey
    plotPoints=np.linspace(start=0, stop=sample_mat.shape[0]-1, num=options.plot.n_points, dtype=int)
    #Plot POI-POI correlation and distributions
    figure, axes=plt.subplots(nrows=model.n_poi, ncols= model.n_poi, squeeze=False)
    for iPOI in range(0,model.n_poi):
        for jPOI in range(0,iPOI+1):
            if iPOI==jPOI:
                n, bins, patches = axes[iPOI, jPOI].hist(sample_mat[:,iPOI], bins=41)
            else:
                axes[iPOI, jPOI].plot(sample_mat[plotPoints,iPOI], sample_mat[plotPoints,jPOI],'b*')
            if jPOI==0:
                axes[iPOI,jPOI].set_ylabel(model.name_poi[iPOI])
            if iPOI==model.n_poi-1:
                axes[iPOI,jPOI].set_xlabel(model.name_poi[jPOI])
            if model.n_poi==1:
                axes[iPOI,jPOI].set_ylabel('Instances')
    figure.tight_layout()
    if options.path:
        plt.savefig(options.path+"POIcorrelation.png")

    #Plot QOI-QOI correlationa and distributions
    figure, axes=plt.subplots(nrows=model.n_qoi, ncols= model.n_qoi, squeeze=False)
    for iQOI in range(0,model.n_qoi):
        for jQOI in range(0,iQOI+1):
            if iQOI==jQOI:
                axes[iQOI, jQOI].hist([eval_mat[:,iQOI]], bins=41)
            else:
                axes[iQOI, jQOI].plot(eval_mat[plotPoints,iQOI], eval_mat[plotPoints,jQOI],'b*')
            if jQOI==0:
                axes[iQOI,jQOI].set_ylabel(model.name_qoi[iQOI])
            if iQOI==model.n_qoi-1:
                axes[iQOI,jQOI].set_xlabel(model.name_qoi[jQOI])
            if model.n_qoi==1:
                axes[iQOI,jQOI].set_ylabel('Instances')
    figure.tight_layout()
    if options.path:
        plt.savefig(options.path+"QOIcorrelation.png")

    #Plot POI-QOI correlation
    figure, axes=plt.subplots(nrows=model.n_qoi, ncols= model.n_poi, squeeze=False)
    for iQOI in range(0,model.n_qoi):
        for jPOI in range(0, model.n_poi):
            axes[iQOI, jPOI].plot(sample_mat[plotPoints,jPOI], eval_mat[plotPoints,iQOI],'b*')
            if jPOI==0:
                axes[iQOI,jPOI].set_ylabel(model.name_qoi[iQOI])
            if iQOI==model.n_qoi-1:
                axes[iQOI,jPOI].set_xlabel(model.name_poi[jPOI])
    if options.path:
        plt.savefig(options.path+"POI_QOIcorrelation.png")
    #Display all figures
    if options.display:
        plt.show()

