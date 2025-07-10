#!/usr/bin/env python3
"""
Distribution Analysis Script for Cellular Simulation Data
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats
from scipy.stats import expon, uniform, binom
import seaborn as sns
from collections import defaultdict
import warnings
warnings.filterwarnings('ignore')

def parse_run_info(run_string):
    """Extract configuration name and repetition number from run string"""
    parts = run_string.split('-')
    if len(parts) >= 2:
        return parts[0], int(parts[1]) if parts[1].isdigit() else 0
    return run_string, 0

def parse_vector_string(vec_str):
    """Parse vector string format into numpy array"""
    if pd.isna(vec_str) or vec_str == '':
        return np.array([])
    return np.fromstring(vec_str.strip(), sep=' ')

def load_distribution_data(filename):
    """Load and categorize vector data for distribution analysis"""
    print(f"Loading data from {filename}...")
    df = pd.read_csv(filename)
    
    # Filter vector data
    vector_df = df[df['type'] == 'vector']
    
    # Initialize data containers
    data_by_type = {
        'inter_arrival': defaultdict(list),
        'cqi': defaultdict(list),
        'packet_size': defaultdict(list)
    }
    
    config_params = {}
    
    print("Processing vectors...")
    for _, row in vector_df.iterrows():
        run = row['run']
        config_name, repetition = parse_run_info(run)
        
        # Parse vectors
        times = parse_vector_string(row['vectime'])
        values = parse_vector_string(row['vecvalue'])
        
        if len(times) == 0 or len(times) != len(values) or len(values) == 0:
            continue
        
        module = row['module']
        name = row['name']
        
        # Categorize data types
        if 'interArrivalTime:vector' in name:
            if len(values) > 0:
                data_by_type['inter_arrival'][config_name].extend(values)
                if config_name not in config_params:
                    config_params[config_name] = {}
        
        elif 'channelQuality:vector' in name:
            # Store CQI values
            if len(values) > 0:
                data_by_type['cqi'][config_name].extend(values)
        
        elif 'packetDimension:vector' in name:
            # Store packet sizes
            if len(values) > 0:
                data_by_type['packet_size'][config_name].extend(values)
    
    # Convert to numpy arrays
    for data_type in data_by_type:
        for config in data_by_type[data_type]:
            data_by_type[data_type][config] = np.array(data_by_type[data_type][config])
    
    return data_by_type, config_params

def qq_plot_exponential(data, lambda_param, ax, title):
    """Create QQ plot against exponential distribution"""
    if len(data) == 0:
        ax.text(0.5, 0.5, 'No data available', ha='center', va='center', transform=ax.transAxes)
        ax.set_title(title)
        return None, None
    
    # Theoretical quantiles for exponential distribution
    sorted_data = np.sort(data)
    n = len(sorted_data)
    theoretical_quantiles = expon.ppf(np.arange(1, n + 1) / (n + 1), scale=1/lambda_param)
    
    # QQ plot
    ax.scatter(theoretical_quantiles, sorted_data, alpha=0.6, s=20)
    
    # Add reference line
    min_val = min(theoretical_quantiles.min(), sorted_data.min())
    max_val = max(theoretical_quantiles.max(), sorted_data.max())
    ax.plot([min_val, max_val], [min_val, max_val], 'r-', linewidth=2, alpha=0.8)
    
    ax.set_xlabel(f'Theoretical Quantiles (Exp(λ={lambda_param:.3f}))')
    ax.set_ylabel('Sample Quantiles')
    ax.set_title(title)
    ax.grid(True, alpha=0.3)
    
    return lambda_param

def qq_plot_uniform(data, min_val, max_val, ax, title):
    """Create QQ plot against uniform distribution"""
    if len(data) == 0:
        ax.text(0.5, 0.5, 'No data available', ha='center', va='center', transform=ax.transAxes)
        ax.set_title(title)
        return None, None
    
    # Theoretical quantiles for uniform distribution
    sorted_data = np.sort(data)
    n = len(sorted_data)
    theoretical_quantiles = uniform.ppf(np.arange(1, n + 1) / (n + 1), loc=min_val, scale=max_val-min_val)
    
    # QQ plot
    ax.scatter(theoretical_quantiles, sorted_data, alpha=0.6, s=20)
    
    # Add reference line
    min_plot = min(theoretical_quantiles.min(), sorted_data.min())
    max_plot = max(theoretical_quantiles.max(), sorted_data.max())
    ax.plot([min_plot, max_plot], [min_plot, max_plot], 'r-', linewidth=2, alpha=0.8)
    
    ax.set_xlabel(f'Theoretical Quantiles (Uniform({min_val},{max_val}))')
    ax.set_ylabel('Sample Quantiles')
    ax.set_title(title)
    ax.grid(True, alpha=0.3)
    
    return (min_val, max_val)

def qq_plot_binomial(data, n_trials, p_success, ax, title):
    """Create QQ plot against binomial distribution (shifted to range 1-15)"""
    if len(data) == 0:
        ax.text(0.5, 0.5, 'No data available', ha='center', va='center', transform=ax.transAxes)
        ax.set_title(title)
        return None, None
    
    # For CQI values 1-15, we need to shift the binomial distribution
    # Binomial(n=14, p) + 1 gives range 1-15
    sorted_data = np.sort(data)
    n = len(sorted_data)
    
    # Generate theoretical quantiles
    theoretical_quantiles = []
    for i in range(1, n + 1):
        prob = i / (n + 1)
        # Find quantile of shifted binomial
        quantile = binom.ppf(prob, n_trials, p_success) + 1
        theoretical_quantiles.append(quantile)
    
    theoretical_quantiles = np.array(theoretical_quantiles)
    
    # QQ plot
    ax.scatter(theoretical_quantiles, sorted_data, alpha=0.6, s=20)
    
    # Add reference line
    min_plot = min(theoretical_quantiles.min(), sorted_data.min())
    max_plot = max(theoretical_quantiles.max(), sorted_data.max())
    ax.plot([min_plot, max_plot], [min_plot, max_plot], 'r-', linewidth=2, alpha=0.8)
    
    ax.set_xlabel(f'Theoretical Quantiles (Binomial({n_trials},{p_success:.2f})+1)')
    ax.set_ylabel('Sample Quantiles')
    ax.set_title(title)
    ax.grid(True, alpha=0.3)
    
    return (n_trials, p_success)

def create_distribution_analysis_plots(data_by_type, config_params):
    """Create comprehensive distribution analysis plots"""
    configs = list(set().union(*[data_by_type[dt].keys() for dt in data_by_type.keys()]))
    
    if not configs:
        print("No data found for analysis!")
        return
    
    # Create plots for each configuration
    for config in configs:
        print(f"\nAnalyzing configuration: {config}")
        
        # Create figure with subplots
        fig = plt.figure(figsize=(20, 15))
        fig.suptitle(f'Distribution Analysis: {config}', fontsize=16, fontweight='bold')
        
        test_results = {}
        
        # 1. Inter-arrival time analysis (Exponential)
        if config in data_by_type['inter_arrival'] and len(data_by_type['inter_arrival'][config]) > 0:
            data = data_by_type['inter_arrival'][config]
            
            # Estimate from data (MLE for exponential is 1/mean)
            #lambda_param = 1.0 / np.mean(data)
            lambda_param = 20000.0
            
            print(f"  Inter-arrival time: {len(data)} samples, λ={lambda_param:.4f}")
            
            # Histogram
            ax1 = plt.subplot(3, 3, 1)
            ax1.hist(data, bins=50, density=True, alpha=0.7, edgecolor='black')
            x_range = np.linspace(0, np.percentile(data, 99), 1000)
            ax1.plot(x_range, expon.pdf(x_range, scale=1/lambda_param), 'r-', linewidth=2, 
                    label=f'Exponential(λ={lambda_param:.3f})')
            ax1.set_title('Inter-arrival Time Distribution')
            ax1.set_xlabel('Time')
            ax1.set_ylabel('Density')
            ax1.legend()
            ax1.grid(True, alpha=0.3)
            
            # QQ Plot
            ax2 = plt.subplot(3, 3, 2)
            qq_plot_exponential(data, lambda_param, ax2, 'Inter-arrival QQ Plot (Exponential)')
            
            # Empirical CDF comparison
            ax3 = plt.subplot(3, 3, 3)
            sorted_data = np.sort(data)
            empirical_cdf = np.arange(1, len(sorted_data) + 1) / len(sorted_data)
            theoretical_cdf = expon.cdf(sorted_data, scale=1/lambda_param)
            ax3.plot(sorted_data, empirical_cdf, 'b-', linewidth=2, label='Empirical CDF')
            ax3.plot(sorted_data, theoretical_cdf, 'r-', linewidth=2, label='Theoretical CDF')
            ax3.set_title('CDF Comparison')
            ax3.set_xlabel('Value')
            ax3.set_ylabel('CDF')
            ax3.legend()
            ax3.grid(True, alpha=0.3)
        
        # 2. CQI analysis (Uniform vs Binomial)
        if config in data_by_type['cqi'] and len(data_by_type['cqi'][config]) > 0:
            data = data_by_type['cqi'][config]
            print(f"  CQI: {len(data)} samples, range=[{data.min():.0f}, {data.max():.0f}]")
            
            # Histogram
            ax5 = plt.subplot(3, 3, 4)
            bins = np.arange(0.5, 16.5, 1)
            counts, _, _ = ax5.hist(data, bins=bins, density=True, alpha=0.7, edgecolor='black')
            
            # Overlay uniform distribution
            uniform_height = 1.0 / 15  # Uniform over 1-15
            ax5.axhline(y=uniform_height, color='red', linestyle='-', linewidth=2, 
                       label='Uniform(1,15)')
            
            # Overlay binomial distribution (try different parameters)
            x_vals = np.arange(1, 16)
            # Try binomial with different parameters
            for n_trials, p in [(14, 0.5)]:
                binomial_probs = binom.pmf(x_vals - 1, n_trials, p)
                ax5.plot(x_vals, binomial_probs, 'o-', alpha=0.7, 
                        label=f'Binomial({n_trials},{p})+1')
            
            ax5.set_title('CQI Distribution')
            ax5.set_xlabel('CQI Value')
            ax5.set_ylabel('Probability/Density')
            ax5.legend()
            ax5.grid(True, alpha=0.3)
            
            # QQ Plot - Uniform
            ax6 = plt.subplot(3, 3, 5)
            qq_plot_uniform(data, 1, 15, ax6, 'CQI QQ Plot (Uniform)')
            
            # QQ Plot - Binomial
            ax7 = plt.subplot(3, 3, 6)
            
            n_est = 14
            p_est = 0.5
            qq_plot_binomial(data, n_est, p_est, ax7, f'CQI QQ Plot (Binomial)')
        
        # 3. Packet size analysis (Uniform)
        if config in data_by_type['packet_size'] and len(data_by_type['packet_size'][config]) > 0:
            data = data_by_type['packet_size'][config]
            print(f"  Packet size: {len(data)} samples, range=[{data.min():.0f}, {data.max():.0f}]")
            
            # Histogram
            ax9 = plt.subplot(3, 3, 7)
            ax9.hist(data, bins=25, density=True, alpha=0.7, edgecolor='black')
            
            # Overlay theoretical uniform distribution
            if data.max() <= 75 and data.min() >= 1:
                uniform_height = 1.0 / (75 - 1)
                ax9.axhline(y=uniform_height, color='red', linestyle='-', linewidth=2, 
                           label='Uniform(1,75)')
            
            ax9.set_title('Packet Size Distribution')
            ax9.set_xlabel('Packet Size')
            ax9.set_ylabel('Density')
            ax9.legend()
            ax9.grid(True, alpha=0.3)
            
            # QQ Plot
            ax10 = plt.subplot(3, 3, 8)
            qq_plot_uniform(data, 1, 75, ax10, 'Packet Size QQ Plot (Uniform)')
            
            # Empirical CDF comparison
            ax11 = plt.subplot(3, 3, 9)
            sorted_data = np.sort(data)
            empirical_cdf = np.arange(1, len(sorted_data) + 1) / len(sorted_data)
            theoretical_cdf = uniform.cdf(sorted_data, loc=1, scale=74)
            ax11.plot(sorted_data, empirical_cdf, 'b-', linewidth=2, label='Empirical CDF')
            ax11.plot(sorted_data, theoretical_cdf, 'r-', linewidth=2, label='Theoretical CDF')
            ax11.set_title('Packet Size CDF Comparison')
            ax11.set_xlabel('Packet Size')
            ax11.set_ylabel('CDF')
            ax11.legend()
            ax11.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(f'distribution_analysis_{config}.png', dpi=300, bbox_inches='tight')
        

def main():
    """Main analysis function"""
    print("Distribution Analysis for Cellular Simulation Data")
    print("="*60)
    
    # Load data
    data_by_type, config_params = load_distribution_data('../csv_results/validation_test41_vector.csv')
    
    # Print summary
    print("\nData Summary:")
    print("-" * 40)
    for data_type, configs in data_by_type.items():
        print(f"{data_type.replace('_', ' ').title()}:")
        for config, data in configs.items():
            if len(data) > 0:
                print(f"  {config}: {len(data)} samples")
    
    if config_params:
        print("\nExtracted Parameters:")
        print("-" * 40)
        for config, params in config_params.items():
            print(f"{config}: {params}")
    
    # Create analysis plots
    create_distribution_analysis_plots(data_by_type, config_params)
    
    print(f"\nAnalysis complete! Check the generated PNG files.")
    print("Distribution analysis plots saved as 'distribution_analysis_<config>.png'")

if __name__ == "__main__":
    main()