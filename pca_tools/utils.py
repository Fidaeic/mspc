#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Jul 31 09:40:07 2021

@author: fidae
"""

import numpy as np
from numpy import linalg as LA
from scipy.stats import f, beta, chi2
from .model import PCA
import pandas as pd
import logging

def optimize(X, n_comps, alpha, numerical_features, statistic='T2', threshold=3):
    """
    This function optimizes a dataset for PCA by iteratively removing out-of-control observations.

    Parameters
    ----------
    X : pd.DataFrame
        The input data to be optimized.
    n_comps : int
        The number of principal components to use in the PCA.
    alpha : float
        The significance level for the control limits. Must be between 0 and 1.
    numerical_features : list
        The list of numerical features to be considered in the PCA.
    statistic : str, optional
        The statistic to use for determining out-of-control observations. Must be either 'T2' for Hotelling's T^2 or 'SPE' for Squared Prediction Error. Default is 'T2'.
    threshold : float, optional
        The threshold for determining out-of-control observations. Observations with a statistic value greater than threshold times the control limit are considered out-of-control. Default is 3.

    Returns
    -------
    X_opt : pd.DataFrame
        The optimized input data with out-of-control observations removed.

    Raises
    ------
    ValueError
        If `statistic` is not 'T2' or 'SPE', `alpha` is not between 0 and 1, `threshold` is not positive, `n_comps` is not greater than 0, `numerical_features` is not a list, or `X` is not a pandas DataFrame.
    """

    # Set up logging
    logging.basicConfig(level=logging.INFO)

    # Validate inputs
    if statistic not in ['T2', 'SPE']:
        raise ValueError("Statistic must be 'T2' or 'SPE'")
    
    if alpha<0 or alpha>1:
        raise ValueError("Alpha must be between 0 and 1")
    
    if threshold<0:
        raise ValueError("Threshold must be positive")
    
    if n_comps<1:
        raise ValueError("Number of components must be greater than 0")
    
    if not isinstance(numerical_features, list):
        raise ValueError("Numerical features must be a list")
    
    if not isinstance(X, pd.DataFrame):
        raise ValueError("X must be a pandas DataFrame")

    # Initialize variables
    keep_indices = np.arange(X.shape[0])

    # Train PCA model
    pca = PCA(n_comps=n_comps)
    pca.train(X, numerical_features=numerical_features, alpha=alpha)

    # Determine control limit and statistic value based on statistic
    if statistic == 'T2':
        control_limit = pca._hotelling_limit_p1
        statistic_value = pca._hotelling
    else:
        control_limit = pca._spe_limit
        statistic_value = pca._spe

    # Calculate proportion of out-of-control observations
    out_of_control = np.sum(statistic_value > control_limit) / len(keep_indices)

    # Iteratively remove out-of-control observations
    while out_of_control > (1 - alpha):
        # Identify out-of-control observations
        drop_indices = np.where(statistic_value > threshold * control_limit)[0]

        # If no observations to drop, break the loop
        if len(drop_indices) == 0:
            break

        # Remove out-of-control observations
        keep_indices = np.delete(keep_indices, drop_indices)

        # Retrain PCA model
        pca.train(X.iloc[keep_indices], numerical_features=numerical_features, alpha=alpha)

        # Recalculate control limit and statistic value
        if statistic == 'T2':
            control_limit = pca._hotelling_limit_p1
            statistic_value = pca._hotelling
        else:
            control_limit = pca._spe_limit
            statistic_value = pca._spe

        # Calculate proportion of out-of-control observations
        out_of_control = np.sum(statistic_value > control_limit) / len(keep_indices)

        # Log progress
        logging.info(f'Processing statistics: {statistic}')
        logging.info(f"{len(drop_indices)} removed observations")
        logging.info(f"Proportion of out of control observations: {out_of_control}")
        logging.info(f"Control limit: {control_limit}")

    # Return optimized data
    return X.iloc[keep_indices]