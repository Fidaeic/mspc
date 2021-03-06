# -*- coding: utf-8 -*-
"""
Created on Mon Apr 20 15:33:50 2020

@author: Fidae El Morer
"""

import numpy as np
import pandas as pd
import statsmodels.api as sm
from numpy import linalg as LA
from sklearn.model_selection import train_test_split
from scipy.stats import f, beta, chi2
import matplotlib.pyplot as plt
import seaborn as sns
sns.set_style(style="darkgrid")
plt.ion()
import math
from matplotlib.patches import Ellipse

from bokeh.io import output_file, reset_output
from bokeh.plotting import figure, show, ColumnDataSource, figure, output_file, show
#from bokeh.models import ColumnDataSource
from bokeh.layouts import row, column, gridplot
from bokeh.models.widgets import Tabs, Panel
from bokeh.models import HoverTool

reset_output()


class PCA(object):
    def __init__(self, df_metadatos, variables, autoescalado = True, tolerancia = 1e-15, verbose = False):

        self.verbose = verbose
        self._autoesc = autoescalado
        self._tolerancia = tolerancia
        self.metadata = df_metadatos
        self.variables = variables

        if not 0 < self._tolerancia < 1:
            raise ValueError('Tolerance must be strictly between 0 and 1')
            
        self._nobs = None
        self._nvars = None    
        self.eigenvals = None
        self.loadings = None
        self.scores = None
        self.rsquare = None
        self.residuals = None
        self.spe = None
        self.t2 = None
        self._ncomps = None
        self.X_train = None
        self.X_test = None
        self.X_opt = None
        self.tau = None
        self.residuals_fit = None
        self.residuals_pred = None
        self.mean_train = None
        self.std_train = None

            
    def fit(self, X_train, ncomps):
        
        self._ncomps = ncomps
        self._nobs, self._nvars = X_train.shape
        self.X_train = X_train
        X_original = X_train
        X = X_train
        mean_train=np.zeros((1, X.shape[1]))
        std_train=np.zeros((1, X.shape[1]))
        for i in range(X.shape[1]):
            mean_train[:,i] = np.mean(X[:,i])
            std_train[:,i] = np.std(X[:,i])
            
        if self._autoesc==True:
            for i in range(X.shape[1]):
                X[:,i]= X[:,i]-np.mean(X[:,i])
                X[:,i]= X[:,i]/np.std(X[:,i])
        
        r2 = []
        T = np.zeros(shape=(self._ncomps, X.shape[0]))
        P_t = np.zeros(shape = (self._ncomps, X.shape[1]))
        vals= np.zeros(self._ncomps)
        dif = self._tolerancia
        
        for i in range(self._ncomps):
            #Iniciamos t como la primera columna de X  
            t = np.array(X[:,0])
            t.shape=(X.shape[0], 1) #Esto sirve para obligar a que t sea un vector columna
            
            #Inicializamos un contador para saber en cu??ntas iteraciones converge el algoritmo y un criterio de parada
            cont=0
            conv=0
                        
            while conv <X.shape[0]:
                
                #Definimos un vector llamado t_previo, que es con el que vamos a empezar el algoritmo
                t_previo = t
                p_t = (np.transpose(t_previo).dot(X))/(np.transpose(t_previo).dot(t_previo))
                p_t = p_t/LA.norm(p_t)
                
                t=X.dot(np.transpose(p_t))
                
                #Comparamos el t calcular con el t_previo, de manera que lo que buscamos es que la diferencia sea menor
                #que el criterio de parada establecido. Para ello, hacemos una prueba l??gica y sumamos todos los valores
                #donde sea verdad. Si es verdad en todos, el algoritmo ha convergido
                conv = np.sum((t-t_previo)<dif)
                cont+=1
            if self.verbose == True:
                print("Componente ", i+1, " converge en ", cont, " iteraciones")
                
            #Calculamos la matriz de residuos y se la asignamos a X para calcular la siguiente componente
            E = X-t.dot(p_t)
            r2.append(1-np.sum(E**2)/np.sum(X_original**2))
            X=E
            
            #Asignamos los vectores t y p a su posici??n en las matrices de scores y loadings
            vals[i] = np.var(t)
            
            T[i]=t.reshape((X.shape[0]))
            P_t[i]=p_t
        T = np.transpose(T)

        self.eigenvals = vals
        self.loadings = P_t
        self.scores = T
        self.rsquared_acc = np.array(r2)
        self.residuals_fit = X_original-T.dot(P_t)
        self.mean_train = mean_train
        self.std_train = std_train
                
    def predict(self, X_test, ncomps):
        
        mean_train = self.mean_train
        std_train = self.std_train
        
        self.X_test = X_test
        X_test = X_test
        
        for i in range(X_test.shape[1]):
            X_test[:,i]= X_test[:,i]-np.mean(X_test[:,i])
            X_test[:,i]= X_test[:,i]/np.std(X_test[:,i])
        
        if ncomps > self._ncomps:
            raise ValueError("The number of components of the plot can't be greater than the number of components of the model")
        
        nvars = X_test.shape[1]
        P_t = self.loadings[:ncomps, :]
        T = X_test.dot(np.transpose(P_t))
        
        tau = []
        t2 = []
        SPE = []
        
        thita = np.cov(T, rowvar=False)
        
        for i in range(X_test.shape[0]):
            z = X_test[i,:]
            
            tau.append(P_t.dot(z))
            
            t2.append((np.transpose(tau[i]).dot(LA.inv(thita))).dot(tau[i]))
            
            e = (np.identity(nvars)-np.transpose(P_t).dot(P_t)).dot(z)
            
            SPE.append(np.transpose(e).dot(e))
        E = X_test - T.dot(P_t)
        
        self.SPE = np.array(SPE)
        self.t2 = np.array(t2)
        self.tau = np.array(tau)
        self.residuals_pred=E

    '''
    PLOTS
    '''
    
    def scree_plot(self):
        data = pd.DataFrame(self.eigenvals)
        
        data.index +=1
        
        
        source = ColumnDataSource(data = dict(
            x = data.index.values,
            y= data.values))
        
        tooltips = [("Component number", "@x"),
                          ("Eigenvalue", "@y")]
        
        p = figure(title='Scree plot', plot_width=800, plot_height=400, x_axis_label = "Number of components", y_axis_label="Eigenvalues", tooltips=tooltips)
        p.line(x=data.index, y=data[0])
        
        p.line(x = data.index, y =1, color='red')
        output_file("Scree_plot.html")
        show(p)
        
    def explain_plot(self):
        
        data = pd.DataFrame(self.rsquared_acc*100, columns = ["rsquared"])
        data.index+=1


        source = ColumnDataSource(data=dict(
            x  = data.index.values,
            value =data.values,
            ))
        
        tooltips = [("Component number", "@x"),
                    ("Accumulated explained variance", "@value")]
        
        p = figure(title="Explained variance", plot_width=800, plot_height=400, x_axis_label = "Number of components", y_axis_label="Accumulated explained variance", tooltips=tooltips)
        p.vbar(x = data.index.values, top = data['rsquared'], width=0.8)
        output_file("Explain_plot.html")
        show(p)
        
    def score_plot(self, comp1, comp2):
        if comp1 <= 0 or comp2 <= 0:
            raise ValueError("The number of components must be greather than 0")

        meta = self.metadata.copy()
        T = self.scores.copy()
        
        data = pd.DataFrame({comp1: T[:, comp1-1],
                             comp2: T[:, comp2-1]})

        source = ColumnDataSource(data=dict(
            x=T[:, comp1-1],
            y=T[:, comp2-1],
            pais=list(meta['PA??S'].values),
            muni=list(meta['MUNICIPIO'].values)))

        tooltips = [
                    ("Observation", "$index"),
                    ("Pais", "@pais"),
                    ("Municipio", "@muni"),
                    ("(x,y)", "($x, $y)")
        ]
        
        p1 = figure(title=f"Gr??fico de scores de las componentes {comp1} y {comp2}",x_axis_label=f"Componente {comp1}", y_axis_label=f"Componente {comp2}", plot_width=800, plot_height=400, tooltips=tooltips)
        p1.circle(source=source, x='x', y='y', size=5, color="navy", alpha=0.5)

        output_file(f"Score_plot_comps_{comp1}-{comp2}.html")
        show(p1)

    def loadings_plot(self, comp):
        if comp <= 0:
            raise ValueError("The number of components must be greather than 0")
        
        P_t = self.loadings
        variables = self.variables.copy()
        
        data = pd.DataFrame({comp: P_t[comp-1,:]})
        
        source = ColumnDataSource(data=dict(
            x = range(P_t.shape[1]),
            valor=P_t[comp-1,:],
            variables = list(variables)))
        
        tooltips = [("Variable", "$index"),
                    ("Nombre de la variable", "@variables"),
                    ("Peso", "@valor")
                    ]
        
        p = figure(title=f"Gr??fico de peso de las variables en la componente {comp}",x_axis_label=f"Variables", y_axis_label=f"Peso de las variables en la componente {comp}",plot_width=800, plot_height=400, tooltips = tooltips)

        p.vbar(source=source, x='x', top = 'valor', width=0.8)
            #x = range(P_t.shape[1]), top = data[comp], width=0.8)
        output_file(f"Loadings_plot_{comp}.html")
        show(p)
        
        
    def compare_loadings(self, comp1, comp2):
        if comp1 <= 0 or comp2 <= 0:
            raise ValueError("The number of components must be greather than 0")
            
        P_t = self.loadings
        var = self.variables.copy()
        
        data = pd.DataFrame({comp1: P_t[comp1-1,:], 
                             comp2: P_t[comp2-1,:]})
        
        source = ColumnDataSource(data=dict(
            x=P_t[comp1-1, :],
            y=P_t[comp2-1, :],
            variable=list(var)))
        
        tooltips = [("Observation", "$index"),
                    ("Variable", "@variable"),
                          ("(x,y)", "($x, $y)")]
        
        p1 = figure(title=f"Gr??fico de loadings de las componentes {comp1} y {comp2}",x_axis_label=f"Componente {comp1}", y_axis_label=f"Componente {comp2}", plot_width=800, plot_height=400, tooltips = tooltips)
        p1.circle(source=source, x='x', y='y', size=5, color="navy", alpha=0.5)

        output_file(f"Loadings_plot_comps_{comp1}-{comp2}.html")
        show(p1)

    def contribution_plot_SPE_p1(self, ncomps, X, obs):

        if ncomps<=0:
            raise ValueError("The number of components must be greather than 0")
            
        T = self.scores[:,:ncomps]
        P_t = self.loadings[:ncomps,:]
               
        E = X-T.dot(P_t)
        
        contrib = E[obs]**2
        
        tooltips = [("Variable", "$index"),
                          ("(x,y)", "($x, $y)")]
        
        p = figure(title = f"Gr??fico de contribuci??n para la observaci??n {obs}", plot_width=800, plot_height=400, tooltips=tooltips)
        p.vbar(x = range(E.shape[1]), top = contrib, width=0.8)
        output_file(f"Loadings_plot_ncomps-{ncomps}_obs-{obs}.html")
        show(p)
        
    def contribution_plot_SPE_p2(self, obs):


        E = self.residuals_pred
        
        contrib = E[obs]**2
        
        tooltips = [("Variable", "$index"),
                          ("(x,y)", "($x, $y)")]
        
        p = figure(title = f"Contribution plot for observation {obs}", plot_width=800, plot_height=400, tooltips=tooltips)
        p.vbar(x = range(E.shape[1]), top = contrib, width=0.8)
        show(p)
        
    def tau_plot_T2_p1(self, obs):

        T = self.scores
        
        lam = [np.var(T[:,i]) for i in range(T.shape[1])]
        
        contrib = [(T[obs,i]/lam[i])**2 for i in range(T.shape[1])]
        
        tooltips = [("Variable", "$index"),
                          ("(x,y)", "($x, $y)")]
        
        p = figure(title = f"Score plot for observation {obs}", plot_width=800, plot_height=400, tooltips=tooltips)
        p.vbar(x = range(T.shape[1]), top = contrib, width=0.8)
        show(p)
        
    def tau_plot_T2_p2(self, obs):

        tau = self.tau
        
        lam = [np.var(tau[:,i]) for i in range(tau.shape[1])]
        
        contrib = [(tau[obs,i]/lam[i])**2 for i in range(tau.shape[1])]

        tooltips = [("Variable", "$index"),
                          ("(x,y)", "($x, $y)")]
        
        p = figure(title = f"Score plot for observation {obs}", plot_width=800, plot_height=400, tooltips=tooltips)
        p.vbar(x = range(tau.shape[1]), top = contrib, width=0.8)
        show(p)
        
    def contribution_plot_T2(self, comp, X, obs):

        if comp <=0:
            raise ValueError("The number of components must be greather than 0")
        
        P_t = self.loadings
        contrib = (P_t[comp-1, :]*X[obs,:]).reshape((X.shape[1]))
        
        tooltips = [("Variable", "$index"),
                          ("(x,y)", "($x, $y)")]
        
        p = figure(title = f"Contribution plot for observation {obs} and component {comp}", plot_width=800, plot_height=400, tooltips=tooltips)
        p.vbar(x = range(P_t.shape[1]), top = contrib, width=0.8)
        show(p)
        
        
    def tau_plot(self, obs, ncomps):

        tau = self.tau
        
        
        p = figure(title = f"Tau plot for observation {obs}", plot_width=800, plot_height=400)
        p.vbar(x = range(1,ncomps+1), top = tau[obs], width=0.8)
        
        show(p)
    
    def T2_plot_p1(self, ncomps, alpha):

        if ncomps <=1:
            raise ValueError("The number of components must be greather than 1")
        
        if ncomps > self._ncomps:
            raise ValueError("The number of components of the plot can't be greater than the number of components of the model")
        
        
        obs = self._nobs
        T = self.scores[:,:ncomps]
        X_train = self.X_train
        
        tau = np.array([np.sum(((T[i])**2)/np.var(T[i])) for i in range(obs)])
    
        
        source=ColumnDataSource(data=dict(
            x=range(0,X_train.shape[0]),
            y=tau,
            a = X_train[:,-4],
            dm = X_train[:, -3],
            m = X_train[:, -2],
            year = X_train[:,-1]))
        
        dfn = ncomps/2
        dfd = (obs-ncomps-1)/2
        const = ((obs-1)**2)/obs
        
        
        tooltips = [("Observation", "@x"),
                    ("T2 value", "@y"),
                    ("Week day", "@a"),
                    ("Day of month", "@dm"),
                    ("Month", "@m"),
                    ("Year", "@year")]

               
        p = figure(title = f"Hotelling's T2 plot for {ncomps} components (Phase I)",plot_width=800, plot_height=400, tooltips=tooltips)
        p.line(x= "x", y="y", source=source)
        p.line(x = "x", y= (beta.ppf(alpha, dfn, dfd))*const, source=source, line_color = 'red')
        show(p)
        
    def SPE_plot_p1(self, ncomps, alpha):

        if ncomps <=0:
            raise ValueError("The number of components must be greather than 0")
            
        if ncomps > self._ncomps:
            raise ValueError("The number of components of the plot can't be greater than the number of components of the model")
        
        X = self.X_train
        T = self.scores[:,:ncomps]
        P_t = self.loadings[:ncomps,:]
               
        E = X-T.dot(P_t)
        
        spe = np.array([np.transpose(E[i,:]).dot(E[i,:]) for i in range(E.shape[0])])
        
        source=ColumnDataSource(data=dict(
            x=range(0,X.shape[0]),
            y=spe,
            a = X[:,-4],
            dm = X[:, -3],
            m = X[:, -2],
            year = X[:,-1]))
        
        tooltips = [("Observation", "@x"),
                    ("SPE value", "@y"),
                    ("Week day", "@a"),
                    ("Day of month", "@dm"),
                    ("Month", "@m"),
                    ("Year", "@year")]
        
        #Calculation of UCL for SPE
        beta = np.mean(spe)
        nu = np.var(spe)
        
        ucl_alpha = nu/(2*beta)*chi2.ppf(alpha, (2*beta**2)/nu)
        
        p = figure(title = f"SPE plot for {ncomps} components (Phase I)", plot_width=800, plot_height=400, tooltips=tooltips)
        
        p.line(x= "x", y="y", source=source)
        
        p.line(x = "x", y= ucl_alpha,source=source, line_color = 'red')
        show(p)
        

    def T2_plot_p2(self, ncomps, alpha):

        if ncomps > self._ncomps:
            raise ValueError("The number of components of the plot can't be greater than the number of components of the model")
        
        obs = self._nobs
        dfn = ncomps
        dfd = obs-ncomps
        const = (((obs**2)-1)*ncomps)/(obs*(obs-ncomps))
        T = self.scores
        X = self.X_test
        
        
        source=ColumnDataSource(data=dict(
            x=range(0,X.shape[0]),
            y=self.t2,
            a = X[:,-4],
            dm = X[:, -3],
            m = X[:, -2],
            year = X[:,-1]))
        
        tooltips = [("Observation", "@x"),
                    ("T2 value", "@y"),
                    ("Week day", "@a"),
                    ("Day of month", "@dm"),
                    ("Month", "@m"),
                    ("Year", "@year")]
        
        p = figure(title = f"T2 plot for {ncomps} components (Phase II)", plot_width=800, plot_height=400, tooltips=tooltips)
        p.line(x= "x", y="y", source=source)

        p.line(x = "x", y= (f.ppf(alpha, dfn, dfd))*const, source=source, line_color = 'red')
        show(p)
        
    def SPE_plot_p2(self, ncomps, alpha):

        if ncomps <=0:
            raise ValueError("The number of components must be greather than 0")
            
        if ncomps > self._ncomps:
            raise ValueError("The number of components of the plot can't be greater than the number of components of the model")
        
        X= self.X_test
        
        source=ColumnDataSource(data=dict(
            x=range(0,X.shape[0]),
            y=self.SPE,
            a = X[:,-4],
            dm = X[:, -3],
            m = X[:, -2],
            year = X[:,-1]))
        
        #Calculation of UCL for 
        n = X.shape[0]
        k = X.shape[1]
        a=ncomps
        c=1
        
        E =self.residuals_pred
        
        s_0 = np.sqrt(np.sum(E**2)/((n-a-1)*(k-a)))
        
        ucl_alpha = (((k-a)/c)*s_0**2)*f.ppf(alpha, k-a, (n-a-1)*(k-a))
        
        tooltips = [("Observation", "@x"),
                    ("SPE value", "@y"),
                    ("Week day", "@a"),
                    ("Day of month", "@dm"),
                    ("Month", "@m"),
                    ("Year", "@year")]
        
        p = figure(title = f"SPE plot for {ncomps} components (Phase II)", plot_width=800, plot_height=400, tooltips=tooltips)
        
        p.line(x= "x", y="y", source=source)
        
        p.line(x = "x", y= ucl_alpha,source=source, line_color = 'red')
        show(p)
        
        
class PCR(PCA):
    def __init__(self, X, ncomps, autoescalado = True, tolerancia = 1e-15, verbose = False):
        PCA.__init__(self, X, ncomps, autoescalado = True, tolerancia = 1e-15, verbose = False)
        self.rsquared_fit = None
        self.rsquared_pred = None
        self.coefs = None
        self.ssr_fit = None
        self.press = None
        self.prediction = None
    
    
    def fit(self, y_train):
        
        self.y_train = y_train
        y_train = np.asarray(y_train)
        
        r2_PCR = []
        T_PCR, P_PCR = self.scores, self.loadings
        
        X_train = self.X

        b = np.linalg.inv(np.transpose(T_PCR).dot(T_PCR)).dot(np.transpose(T_PCR)).dot(y_train)
        
        B_PCR = np.transpose(P_PCR).dot(b)
        
        y_hat_PCR = X_train.dot(B_PCR)
        
        r2_PCR = 100*(1- np.sum((y_train-y_hat_PCR)**2)/np.sum((y_train-np.mean(y))**2))
    
        self.rsquared_fit = r2_PCR
        self.coefs = B_PCR
        self.ssr_fit = np.sum((y_train-y_hat_PCR)**2)
        
    def predict(self, X_test, y_test):
        
        B_PCR = self.coefs
        
        y_prediction = X_test.dot(B_PCR)
        
        self.prediction = y_prediction
        r2_pred = 100*(1- np.sum((y_test-y_prediction)**2)/np.sum((y_test-np.mean(y_test))**2))
        self.rsquared_pred = r2_pred
        self.press = np.sum((y_prediction-y_test)**2)

class PLS(object):
    def __init__(self, X,y,ncomps, tol=1e-15, autoescalado=True):
        
        self.X = np.asarray(X)
        self.y = np.asarray(y)
        self._ncomps = ncomps
        self._autoesc = autoescalado
        self._tolerancia = tol
        self._nobs, self._nvars = self.X.shape
        
        self.T = None
        self.P_t = None
        self.U = None
        self.C_t = None
        self.W = None
        
        self.rsquare_X = None
        self.rsquare_y = None
        
        
    def nipals(self, X, y, n_componentes, autoesc=True):
        X_original = self.X
        X = self.X
        
        y_original = self.y
        y=self.y
        
        dif = self._tolerancia
            
        
        #Establecemos la posibilidad de autoescalar. Por defecto, la funci??n autoescalar??
        if self._autoesc==True:
            for i in range(X.shape[1]):
                X[:,i]= X[:,i]-np.mean(X[:,i])
                X[:,i]= X[:,i]/np.std(X[:,i])
                
            for i in range(y.shape[1]):   
                y[:,i]= y[:,i]-np.mean(y[:,i])
                y[:,i]= y[:,i]/np.std(y[:,i])
        
        
        if not 0 < self._tolerancia < 1:
            raise ValueError('Tolerance must be strictly between 0 and 1')
                
        print("********* Algoritmo NIPALS para PLS ***********")
        #Inicializamos las matrices de scores y de loadings seg??n el n??mero de componentes propuesto
        r2_X = []
        T = np.zeros(shape=(self._ncomps, X.shape[0]))
        P_t = np.zeros(shape = (self._ncomps, X.shape[1]))
        
        r2_y = []
        U = np.zeros(shape=(self._ncomps, y.shape[0]))
        C_t = np.zeros(shape = (self._ncomps, y.shape[1]))
        
        W_t = np.zeros(shape = (self._ncomps, y.shape[1]))
        
        
        for i in range(self._ncomps):
            
            #Iniciamos u como la primera columna de Y
            u = np.array(y[:,0])
            u.shape=(y.shape[0], 1) #Esto sirve para obligar a que t sea un vector columna
            
            cont=0
            conv=0
            
            while conv<y.shape[0]:
                u_previo = u
                w_t = (np.transpose(u_previo).dot(X))/(np.transpose(u_previo).dot(u_previo))
                w_t = w_t/LA.norm(w_t)
                
                t=X.dot(np.transpose(w_t))
                
                c_t = np.transpose(t).dot(y)/(np.transpose(t).dot(t))
                
                u = y.dot(np.transpose(c_t))/(c_t.dot(np.transpose(c_t)))
                conv = np.sum((u-u_previo)<dif)
                cont+=1
                
            p_t=np.transpose(t).dot(X)/(np.transpose(t).dot(t))
            
            print("Componente ", i+1, " converge en ", cont, " iteraciones")
            E = X-t.dot(p_t)
            F=y-t.dot(c_t)
            
            r2_X.append(1-np.sum(E**2)/np.sum(X_original**2))
            r2_y.append(1-np.sum(F**2)/np.sum(y_original**2))
            
            X=E
            Y=F
            
            T[i]=t.reshape((X.shape[0]))
            P_t[i]=p_t
            
            U[i]=u.reshape((X.shape[0]))
            C_t[i]=c_t
            
            W_t[i]= w_t
            
        T = np.transpose(T)
        U = np.transpose(U)
        
        self.T = T
        self.P_t = P_t
        self.U = U
        self.C_t = C_t
        self.W = W_t
        
        self.rsquare_X = r2_X
        self.rsquare_y = r2_Y
    

def optimize_SPE(X_train, ncomps, alpha, threshold, iterations=500, tol=1e-15):
    limit_SPE=1000
    highest=1000
    tam = X_train.shape[0]
    
    while highest > 0:
        model = PCA(tolerancia=tol)
        model.fit(X_train, ncomps)
            
        T = model.scores
        P_t = model.loadings
        E=X_train-T.dot(P_t)
                
        obs = X_train.shape[0]
    
        spe = np.array([np.transpose(E[i,:]).dot(E[i,:]) for i in range(E.shape[0])])
        b = np.mean(spe)
        nu = np.var(spe)
    
        ucl_SPE = nu/(2*b)*chi2.ppf(alpha, (2*b**2)/nu)
        
        greater = []
        for k in range(obs):
            if spe[k]>threshold*ucl_SPE:
                greater.append(k)
                
        if max(spe)>threshold*ucl_SPE:
            X_train = np.delete(X_train,np.where(spe ==max(spe)),0)
    
        highest = len(greater) 
    
    
    while limit_SPE > (1-alpha)*tam:

        
        model = PCA(tolerancia=tol)
        model.fit(X_train, ncomps)
        
        T = model.scores
        P_t = model.loadings
        E=X_train-T.dot(P_t)
                
        obs = X_train.shape[0]

        spe = np.array([np.transpose(E[i,:]).dot(E[i,:]) for i in range(E.shape[0])])
        b = np.mean(spe)
        nu = np.var(spe)
    
        ucl_SPE = nu/(2*b)*chi2.ppf(alpha, (2*b**2)/nu)
        
        greater = []
        for k in range(obs):
            if spe[k]>ucl_SPE:
                greater.append(k)
                
        if max(spe)>ucl_SPE:
                k = np.where(spe ==max(spe))
                X_train = np.delete(X_train, k, 0)      
                
        limit_SPE= len(greater)

    model= PCA(tolerancia = tol, autoescalado = False)
    X_opt = X_train
    model.fit(X_opt, ncomps)    
    return(X_opt, model)
    
def optimize_T2(X_train, ncomps, alpha, threshold, iterations=10, tol=1e-15):
    limit_T2=1000
    tam = X_train.shape[0]
    highest = 1000
    
    while highest > 0:
        model = PCA(tolerancia=tol)
        model.fit(X_train, ncomps)
            
        T = model.scores
        P_t = model.loadings
                
        obs = X_train.shape[0]
        
        dfn = ncomps/2
        dfd = (obs-ncomps-1)/2
        const = ((obs-1)**2)/obs
        tau = np.array([np.sum(((T[i])**2)/np.var(T[i])) for i in range(obs)])
    
        ucl_T2 = (beta.ppf(alpha, dfn, dfd))*const
        
        greater = []
        for k in range(obs):
            if tau[k]>threshold*ucl_T2:
                greater.append(k)
                
        if max(tau)>threshold*ucl_T2:
            X_train = np.delete(X_train,np.where(tau ==max(tau)),0)
    
        highest = len(greater)

    while limit_T2 > (1-alpha)*tam:
        
        model = PCA(tolerancia = tol)
        model.fit(X_train, ncomps)
        
        T = model.scores
        
        obs = X_train.shape[0]
        
        dfn = ncomps/2
        dfd = (obs-ncomps-1)/2
        const = ((obs-1)**2)/obs
        tau = np.array([np.sum(((T[i])**2)/np.var(T[i])) for i in range(obs)])
    
        ucl_T2 = (beta.ppf(alpha, dfn, dfd))*const
        
        greater = []
        for k in range(X_train.shape[0]):
            if tau[k]>ucl_T2:
                greater.append(k)
                
        if max(tau)>ucl_T2:
                l = np.where(tau ==max(tau))
                X_train = np.delete(X_train, l, 0)

        limit_T2= len(greater)
        

    model= PCA(tolerancia = tol, autoescalado = False)
    X_opt = X_train
    model.fit(X_opt, ncomps)
    
    return(X_opt, model)