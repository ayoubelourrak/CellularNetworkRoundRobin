#!/usr/bin/env python3
"""
Analysis script for CellularRoundRobin
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats
import seaborn as sns
from matplotlib.gridspec import GridSpec

def load_and_process_data(filename):
    """Load CSV data and extract relevant information"""
    # Read the CSV file
    df = pd.read_csv(filename)
    
    # Extract simulation parameters
    sim_params = extract_simulation_parameters(df)
    
    # Process different metrics
    results = {
        'response_time': process_response_time(df),
        'throughput': process_throughput(df, sim_params),
        'system_throughput': process_system_throughput(df, sim_params),
        'queue_length': process_queue_length(df),
        'scheduled_users': process_scheduled_users(df),
        'resource_utilization': process_resource_utilization(df),
        'arrival_rates': extract_arrival_rates(df),
        'sim_params': sim_params
    }
    
    return results

def extract_simulation_parameters(df):
    """Extract simulation time and warmup period"""
    sim_time_rows = df[(df['type'] == 'config') & (df['attrname'] == 'sim-time-limit')]
    warmup_rows = df[(df['type'] == 'config') & (df['attrname'] == 'warmup-period')]
    
    sim_params = {}
    for _, row in sim_time_rows.iterrows():
        run = row['run']
        sim_time = float(row['attrvalue'].replace('s', ''))
        
        warmup_row = warmup_rows[warmup_rows['run'] == run]
        warmup = float(warmup_row.iloc[0]['attrvalue'].replace('s', '')) if not warmup_row.empty else 0
        
        sim_params[run] = {
            'sim_time': sim_time,
            'warmup': warmup,
            'effective_time': sim_time - warmup
        }
    
    return sim_params

def extract_arrival_rates(df):
    """Extract arrival rates for all users"""
    arrival_params = df[(df['type'] == 'param') & 
                       (df['name'] == 'arrivalRate') &
                       (df['module'].str.contains('CellularNetwork.user'))]
    
    arrival_rates = {}
    for _, row in arrival_params.iterrows():
        run = row['run']
        # Extract user ID from module name
        user_id = int(row['module'].split('[')[1].split(']')[0])
        arrival_rate = float(row['value'].replace('Hz', ''))
        
        if run not in arrival_rates:
            arrival_rates[run] = {}
        arrival_rates[run][user_id] = arrival_rate
    
    return arrival_rates

def process_response_time(df):
    """Process response time statistics for all users"""
    response_stats = df[(df['type'] == 'statistic') & 
                       (df['name'] == 'responseTime:stats') &
                       (df['module'].str.contains('queue'))]
    
    results = []
    for _, row in response_stats.iterrows():
        # Extract user ID from module name
        user_id = int(row['module'].split('[')[1].split(']')[0])
        
        results.append({
            'run': row['run'],
            'user_id': user_id,
            'mean': row['mean'],
            'stddev': row['stddev'],
            'count': row['count'],
            'min': row['min'],
            'max': row['max']
        })
    
    return pd.DataFrame(results)

def process_throughput(df, sim_params):
    """Process user throughput (bit transmitted per second)"""
    bytes_transmitted = df[(df['type'] == 'scalar') & 
                          (df['name'] == 'bytesTransmitted:sum') &
                          (df['module'].str.contains('queue'))]
    
    results = []
    for _, row in bytes_transmitted.iterrows():
        run = row['run']
        user_id = int(row['module'].split('[')[1].split(']')[0])
        
        if run in sim_params:
            effective_time = sim_params[run]['effective_time']
            throughput = float(row['value']) * 8.0 / effective_time if effective_time > 0 else 0
            
            results.append({
                'run': run,
                'user_id': user_id,
                'bytes_transmitted': float(row['value']),
                'throughput_bps': throughput,
                'throughput_mbps': throughput / 1_000_000
            })
    
    return pd.DataFrame(results)

def process_system_throughput(df, sim_params):
    """Process system-wide throughput"""
    system_bytes = df[(df['type'] == 'scalar') & 
                     (df['name'] == 'systemTransmittedBytes:sum') &
                     (df['module'] == 'CellularNetwork.baseStation.scheduler')]
    
    results = []
    for _, row in system_bytes.iterrows():
        run = row['run']
        
        if run in sim_params:
            effective_time = sim_params[run]['effective_time']
            throughput = float(row['value']) * 8.0 / effective_time if effective_time > 0 else 0
            
            results.append({
                'run': run,
                'system_bytes': float(row['value']),
                'system_throughput_bps': throughput,
                'system_throughput_mbps': throughput / 1_000_000
            })
    
    return pd.DataFrame(results)

def process_queue_length(df):
    """Process queue length statistics"""
    queue_stats = df[(df['type'] == 'scalar') & 
                    (df['name'] == 'queueLength:timeavg') &
                    (df['module'].str.contains('queue'))]
    
    results = []
    for _, row in queue_stats.iterrows():
        user_id = int(row['module'].split('[')[1].split(']')[0])
        
        results.append({
            'run': row['run'],
            'user_id': user_id,
            'avg_queue_length': float(row['value'])
        })
    
    return pd.DataFrame(results)

def process_scheduled_users(df):
    """Process scheduled users per round statistics"""
    scheduled = df[(df['type'] == 'statistic') & 
                  (df['name'] == 'scheduledUsersPerRound:stats') &
                  (df['module'] == 'CellularNetwork.baseStation.scheduler')]
    
    results = []
    for _, row in scheduled.iterrows():
        results.append({
            'run': row['run'],
            'mean_scheduled_users': row['mean'],
            'stddev_scheduled_users': row['stddev'],
            'min_scheduled_users': row['min'],
            'max_scheduled_users': row['max']
        })
    
    return pd.DataFrame(results)

def process_resource_utilization(df):
    """Process resource utilization statistics"""
    utilization = df[(df['type'] == 'statistic') & 
                    (df['name'] == 'resourceUtilization:stats') &
                    (df['module'] == 'CellularNetwork.baseStation.scheduler')]
    
    results = []
    for _, row in utilization.iterrows():
        results.append({
            'run': row['run'],
            'mean_rb_utilization': row['mean'],
            'stddev_rb_utilization': row['stddev'],
            'min_rb_utilization': row['min'],
            'max_rb_utilization': row['max']
        })
    
    return pd.DataFrame(results)

def group_by_arrival_rate(metric_df, arrival_rates):
    """Group results by arrival rate configuration"""
    
    grouped = {}
    for _, row in metric_df.iterrows():
        run = row['run']
        if run in arrival_rates:
            # Check if single user or multi-user
            num_users = len(arrival_rates[run])
            
            if num_users == 1:
                # Single user case
                rate_key = arrival_rates[run][0]
            else:
                # Multi-user case
                rates = [arrival_rates[run].get(i, 0) for i in range(num_users)]
                rate_key = tuple(rates)
            
            if rate_key not in grouped:
                grouped[rate_key] = []
            
            grouped[rate_key].append(row)
    
    return grouped

def calculate_statistics(values):
    """Calculate mean and confidence intervals"""
    if len(values) == 0:
        return None
        
    n = len(values)
    mean = np.mean(values)
    std = np.std(values, ddof=1) if n > 1 else 0
    
    # Calculate 99% confidence interval using t-distribution
    if n > 1:
        alpha = 0.01
        df_t = n - 1
        t_critical = stats.t.ppf(1 - alpha/2, df_t)
        sem = std / np.sqrt(n)
        ci_lower = mean - t_critical * sem
        ci_upper = mean + t_critical * sem
    else:
        ci_lower = ci_upper = mean
    
    return {
        'mean': mean,
        'std': std,
        'ci_lower': ci_lower,
        'ci_upper': ci_upper,
        'n': n
    }

def create_comprehensive_plots(results):
    """Create individual plots and save each as a separate PNG file"""
    # Set style
    plt.style.use('seaborn-v0_8-darkgrid')
    
    # 1. Response Time per User
    fig1, ax1 = plt.subplots(figsize=(10, 6))
    plot_response_time_per_user(results, ax1)
    plt.tight_layout()
    plt.savefig('response_time_per_user.png', dpi=300, bbox_inches='tight')
    print("Saved: response_time_per_user.png")
    
    # 2. User Throughput
    fig2, ax2 = plt.subplots(figsize=(8, 6))
    plot_user_throughput(results, ax2)
    plt.tight_layout()
    plt.savefig('user_throughput.png', dpi=300, bbox_inches='tight')
    print("Saved: user_throughput.png")
    
    # 3. System Throughput
    fig3, ax3 = plt.subplots(figsize=(8, 6))
    plot_system_throughput(results, ax3)
    plt.tight_layout()
    plt.savefig('system_throughput.png', dpi=300, bbox_inches='tight')
    print("Saved: system_throughput.png")
    
    # 4. Queue Length
    fig4, ax4 = plt.subplots(figsize=(8, 6))
    plot_queue_length(results, ax4)
    plt.tight_layout()
    plt.savefig('queue_length.png', dpi=300, bbox_inches='tight')
    print("Saved: queue_length.png")
    
    # 5. Resource Utilization
    fig5, ax5 = plt.subplots(figsize=(8, 6))
    plot_resource_utilization(results, ax5)
    plt.tight_layout()
    plt.savefig('resource_utilization.png', dpi=300, bbox_inches='tight')
    print("Saved: resource_utilization.png")
    
    # 6. Scheduled Users per Round
    fig6, ax6 = plt.subplots(figsize=(10, 6))
    plot_scheduled_users(results, ax6)
    plt.tight_layout()
    plt.savefig('scheduled_users_per_round.png', dpi=300, bbox_inches='tight')
    print("Saved: scheduled_users_per_round.png")
    
    # 7. Summary Statistics Table
    fig7, ax7 = plt.subplots(figsize=(10, 8))
    plot_summary_table(results, ax7)
    plt.tight_layout()
    plt.savefig('summary_statistics_table.png', dpi=300, bbox_inches='tight')
    print("Saved: summary_statistics_table.png")
    
    # Also create a comprehensive figure with all plots
    fig_all = plt.figure(figsize=(16, 20))
    gs = GridSpec(6, 2, figure=fig_all, hspace=0.3, wspace=0.3)
    
    # 1. Response Time per User (spans full width)
    ax1_all = fig_all.add_subplot(gs[0, :])
    plot_response_time_per_user(results, ax1_all)
    
    # 2. User Throughput
    ax2_all = fig_all.add_subplot(gs[1, 0])
    plot_user_throughput(results, ax2_all)
    
    # 3. System Throughput
    ax3_all = fig_all.add_subplot(gs[1, 1])
    plot_system_throughput(results, ax3_all)
    
    # 4. Queue Length
    ax4_all = fig_all.add_subplot(gs[2, 0])
    plot_queue_length(results, ax4_all)
    
    # 5. Resource Utilization
    ax5_all = fig_all.add_subplot(gs[2, 1])
    plot_resource_utilization(results, ax5_all)
    
    # 6. Scheduled Users per Round (spans full width)
    ax6_all = fig_all.add_subplot(gs[3, :])
    plot_scheduled_users(results, ax6_all)
    
    # 7. Summary Statistics Table (spans bottom area)
    ax7_all = fig_all.add_subplot(gs[4:, :])
    plot_summary_table(results, ax7_all)
    
    plt.suptitle('CellularRoundRobin Validation Test Analysis', fontsize=16, fontweight='bold')
    
    return fig_all

def plot_response_time_per_user(results, ax):
    """Plot response time for each user with confidence intervals"""
    response_df = results['response_time']
    arrival_rates = results['arrival_rates']
    
    # Group by arrival rate and user
    grouped = group_by_arrival_rate(response_df, arrival_rates)
    
    # Prepare data for plotting - aggregate across repetitions
    plot_data = {}
    rate_labels = []
    
    for rate_key in sorted(grouped.keys()):
        rows = grouped[rate_key]
        
        if isinstance(rate_key, tuple):
            rate_label = f"{rate_key[0]/1000}"
        else:
            rate_label = f"{rate_key/1000}"
        
        if rate_label not in rate_labels:
            rate_labels.append(rate_label)
        
        # Group by user
        user_values = {}
        for row in rows:
            user_id = row['user_id'] if 'user_id' in row else 0
            if user_id not in user_values:
                user_values[user_id] = []
            user_values[user_id].append(row['mean'])
        
        # Calculate statistics for each user
        for user_id, values in user_values.items():
            if user_id not in plot_data:
                plot_data[user_id] = {'rates': [], 'means': [], 'ci_lower': [], 'ci_upper': []}
            
            stats = calculate_statistics(values)
            plot_data[user_id]['rates'].append(rate_label)
            plot_data[user_id]['means'].append(stats['mean'])
            plot_data[user_id]['ci_lower'].append(stats['ci_lower'])
            plot_data[user_id]['ci_upper'].append(stats['ci_upper'])
    
    # Plot each user with error bars
    colors = plt.cm.tab10(np.linspace(0, 1, len(plot_data)))
    x_pos = np.arange(len(rate_labels))
    
    for idx, (user_id, data) in enumerate(plot_data.items()):
        means = data['means']
        ci_lower = data['ci_lower']
        ci_upper = data['ci_upper']
        
        # Calculate error bars
        yerr_lower = np.array(means) - np.array(ci_lower)
        yerr_upper = np.array(ci_upper) - np.array(means)
        yerr = [yerr_lower, yerr_upper]
        
        ax.errorbar(x_pos, means, yerr=yerr, 
                   fmt='o-', label=f'User {user_id}', 
                   color=colors[idx], markersize=8,
                   capsize=5, linewidth=2)
    
    ax.set_xticks(x_pos)
    ax.set_xticklabels(rate_labels, rotation=45, ha='right')
    ax.set_xlabel('Arrival Rate (kHz)')
    ax.set_ylabel('Mean Response Time (s)')
    ax.locator_params(axis='y', nbins=20)
    ax.set_title('Response Time by User and Arrival Rate\n(Mean ± 99% CI from 20 repetitions)')
    ax.legend()
    ax.grid(True, alpha=0.3)
 
def plot_user_throughput(results, ax):
    """Plot throughput for each user with confidence intervals"""
    throughput_df = results['throughput']
    arrival_rates = results['arrival_rates']
    
    # Group by arrival rate
    grouped = group_by_arrival_rate(throughput_df, arrival_rates)
    
    # Prepare data - aggregate across repetitions
    plot_data = {}
    rate_keys_sorted = sorted(grouped.keys())
    rate_labels = [f"{rate_key/1000}" if not isinstance(rate_key, tuple) else f"{rate_key[0]/1000}"
                   for rate_key in rate_keys_sorted]
    
    # Initialize plot_data structure for all users and rates
    all_user_ids = sorted(list(set(throughput_df['user_id'])))
    for user_id in all_user_ids:
        plot_data[user_id] = {'rates_numeric': [], 'means': [], 'ci_lower': [], 'ci_upper': []}

    for rate_key in rate_keys_sorted:
        rows = grouped[rate_key]
        
        # Group by user for the current rate_key
        user_values_at_rate = {}
        for row in rows:
            user_id = row['user_id']
            if user_id not in user_values_at_rate:
                user_values_at_rate[user_id] = []
            user_values_at_rate[user_id].append(row['throughput_mbps'])
        
        # Calculate statistics for each user at this specific rate_key
        for user_id in all_user_ids:
            values = user_values_at_rate.get(user_id, [])
            stats = calculate_statistics(values)
            
            # Append data to the pre-initialized structure
            plot_data[user_id]['rates_numeric'].append(rate_key/1000 if not isinstance(rate_key, tuple) else rate_key[0]/1000)
            plot_data[user_id]['means'].append(stats['mean'])
            plot_data[user_id]['ci_lower'].append(stats['ci_lower'])
            plot_data[user_id]['ci_upper'].append(stats['ci_upper'])
    
    # Define a colormap for different users
    colors = plt.get_cmap('viridis', len(plot_data))
    
    # Plot lines with confidence intervals
    for idx, (user_id, data) in enumerate(plot_data.items()):
        
        # Convert to numpy arrays for plotting
        rates_numeric_arr = np.array(data['rates_numeric'])
        means_arr = np.array(data['means'])
        ci_lower_arr = np.array(data['ci_lower'])
        ci_upper_arr = np.array(data['ci_upper'])
        
        # Plot the mean line
        ax.plot(rates_numeric_arr, means_arr, 
                marker='o', linestyle='-', 
                color=colors(idx), 
                label=f'User {user_id} Mean')
        
        # Plot the confidence interval as a shaded area
        ax.fill_between(rates_numeric_arr, ci_lower_arr, ci_upper_arr, 
                        color=colors(idx), alpha=0.2)
        
    # Set x-axis ticks to be the numeric rate keys
    ax.set_xticks(plot_data[0]['rates_numeric'])
    ax.set_xticklabels(rate_labels, rotation=45, ha='right')
    ax.set_xlabel('Arrival Rate (kHz)')
    ax.set_ylabel('Throughput (Mbps)')
    ax.locator_params(axis='y', nbins=25)
    ax.set_title('User Throughput\n(Mean ± 99% CI from 20 repetitions)')
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')

def plot_system_throughput(results, ax):
    """Plot system-wide throughput with confidence intervals"""
    system_df = results['system_throughput']
    arrival_rates = results['arrival_rates']
    
    # Group by arrival rate
    grouped = group_by_arrival_rate(system_df, arrival_rates)
    
    # Calculate statistics
    rates = []
    means = []
    ci_lower = []
    ci_upper = []
    
    for rate_key in sorted(grouped.keys()):
        rows = grouped[rate_key]
        values = [row['system_throughput_mbps'] for row in rows]
        stats = calculate_statistics(values)
        
        if stats:
            rate_label = f"{rate_key/1000}" if not isinstance(rate_key, tuple) else f"{rate_key[0]/1000}"
            rates.append(rate_label)
            means.append(stats['mean'])
            ci_lower.append(stats['ci_lower'])
            ci_upper.append(stats['ci_upper'])
    
    # Plot with error bars
    x_pos = range(len(rates))
    yerr_lower = np.array(means) - np.array(ci_lower)
    yerr_upper = np.array(ci_upper) - np.array(means)
    yerr = [yerr_lower, yerr_upper]
    
    bars = ax.bar(x_pos, means, yerr=yerr, 
                   capsize=8, alpha=0.7,
                   color='steelblue', edgecolor='darkblue', linewidth=2)
    
    # Add value labels on bars
    for i, (bar, mean) in enumerate(zip(bars, means)):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + yerr_upper[i] + 0.05,
                f'{mean:.3f}', ha='center', va='bottom', fontsize=10)
    
    ax.set_xticks(x_pos)
    ax.set_xticklabels(rates, rotation=45, ha='right')
    ax.set_xlabel('Arrival Rate (kHz)')
    ax.set_ylabel('System Throughput (Mbps)')
    ax.set_title('System-wide Throughput\n(Mean ± 99% CI from 20 repetitions)')
    ax.grid(True, alpha=0.3, axis='y')

def plot_queue_length(results, ax):
    """Plot average queue length with confidence intervals"""
    queue_df = results['queue_length']
    arrival_rates = results['arrival_rates']
    
    # Group by arrival rate and user
    grouped = group_by_arrival_rate(queue_df, arrival_rates)
    
    # Prepare data - aggregate across repetitions
    plot_data = {}
    rate_labels = []
    
    for rate_key in sorted(grouped.keys()):
        rows = grouped[rate_key]
        rate_label = f"{rate_key/1000}" if not isinstance(rate_key, tuple) else f"{rate_key[0]/1000}"
        
        if rate_label not in rate_labels:
            rate_labels.append(rate_label)
        
        # Group by user
        user_values = {}
        for row in rows:
            user_id = row['user_id']
            if user_id not in user_values:
                user_values[user_id] = []
            user_values[user_id].append(row['avg_queue_length'])
        
        # Calculate statistics for each user
        for user_id, values in user_values.items():
            if user_id not in plot_data:
                plot_data[user_id] = {'rates': [], 'means': [], 'ci_lower': [], 'ci_upper': []}
            
            stats = calculate_statistics(values)
            plot_data[user_id]['rates'].append(rate_label)
            plot_data[user_id]['means'].append(stats['mean'])
            plot_data[user_id]['ci_lower'].append(stats['ci_lower'])
            plot_data[user_id]['ci_upper'].append(stats['ci_upper'])
    
    # Plot with error bars
    x_pos = np.arange(len(rate_labels))
    colors = plt.cm.tab10(np.linspace(0, 1, len(plot_data)))
    
    for idx, (user_id, data) in enumerate(plot_data.items()):
        means = data['means']
        ci_lower = data['ci_lower']
        ci_upper = data['ci_upper']
        
        yerr = [np.array(means) - np.array(ci_lower), 
                np.array(ci_upper) - np.array(means)]
        
        ax.errorbar(x_pos, means, yerr=yerr, 
                   fmt='o-', label=f'User {user_id}', 
                   color=colors[idx], markersize=8,
                   capsize=5, linewidth=2)
    
    ax.set_xticks(x_pos)
    ax.set_xticklabels(rate_labels, rotation=45, ha='right')
    ax.set_xlabel('Arrival Rate (kHz)')
    ax.set_ylabel('Average Queue Length')
    ax.locator_params(axis='y', nbins=20)
    ax.set_title('Queue Length by User\n(Mean ± 99% CI from 20 repetitions)')
    ax.legend()
    ax.grid(True, alpha=0.3)

def plot_resource_utilization(results, ax):
    """Plot resource block utilization with confidence intervals"""
    util_df = results['resource_utilization']
    arrival_rates = results['arrival_rates']
    
    # Group by arrival rate
    grouped = group_by_arrival_rate(util_df, arrival_rates)
    
    # Calculate statistics
    rates_numeric = [] 
    rates_labels = []  
    means = []
    ci_lower = []
    ci_upper = []
    
    for rate_key in sorted(grouped.keys()):
        rows = grouped[rate_key]
        # Get the mean RB utilization from each repetition
        values = [row['mean_rb_utilization'] for row in rows]
        
        if values:
            stats = calculate_statistics(values)
            rate_label = f"{rate_key/1000}" if not isinstance(rate_key, tuple) else f"{rate_key[0]/1000}"
            rates_labels.append(rate_label)
            rates_numeric.append(rate_key/1000 if not isinstance(rate_key, tuple) else rate_key[0]/1000)
            means.append(stats['mean'])
            ci_lower.append(stats['ci_lower'])
            ci_upper.append(stats['ci_upper'])
    
    
    means = np.array(means)
    ci_lower = np.array(ci_lower)
    ci_upper = np.array(ci_upper)

    # Plot the line for the means
    ax.plot(rates_numeric, means, marker='o', linestyle='-', color='blue', label='Mean Utilization')
    
    # Plot the confidence interval as a shaded area
    ax.fill_between(rates_numeric, ci_lower, ci_upper, color='blue', alpha=0.2, label='99% CI')
    
    # Set x-ticks based on the numeric rates and label them
    ax.set_xticks(rates_numeric)
    ax.set_xticklabels(rates_labels, rotation=45, ha='right')
    ax.set_xlabel('Arrival Rate (Hz)')
    ax.set_ylabel('Resource Blocks Used')
    ax.set_title('Mean Resource Block Utilization\n(Mean ± 99% CI from 20 repetitions)')
    ax.axhline(y=25, color='r', linestyle='--', linewidth=2, label='Max RBs (25)')
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')
    ax.set_ylim(0, 30)
    ax.set_yticks(np.arange(0,30,1))

def plot_scheduled_users(results, ax):
    """Plot scheduled users per round with confidence intervals"""
    scheduled_df = results['scheduled_users']
    arrival_rates = results['arrival_rates']
    
    # Group by arrival rate
    grouped = group_by_arrival_rate(scheduled_df, arrival_rates)
    
    # Prepare data
    rates = []
    mean_means = []
    mean_ci_lower = []
    mean_ci_upper = []
    
    for rate_key in sorted(grouped.keys()):
        rows = grouped[rate_key]
        
        if rows:
            rate_label = f"{rate_key/1000}" if not isinstance(rate_key, tuple) else f"{rate_key[0]/1000}"
            rates.append(rate_label)
            
            # Collect values from all repetitions
            mean_vals = [row['mean_scheduled_users'] for row in rows]
            
            # Calculate statistics for mean scheduled users
            stats = calculate_statistics(mean_vals)
            mean_means.append(stats['mean'])
            mean_ci_lower.append(stats['ci_lower'])
            mean_ci_upper.append(stats['ci_upper'])
    
    # Plot
    x_pos = np.arange(len(rates))
    width = 0.35
    
    # Mean bars with confidence intervals
    yerr_lower = np.array(mean_means) - np.array(mean_ci_lower)
    yerr_upper = np.array(mean_ci_upper) - np.array(mean_means)
    yerr = [yerr_lower, yerr_upper]
    
    bars_mean = ax.bar(x_pos + width/2, mean_means, width, 
                        yerr=yerr, capsize=5,
                        label='Mean (± 99% CI)', alpha=0.7, color='orange')
    
    # Add max values as points with lines
    for i, (x, mean) in enumerate(zip(x_pos, mean_means)):
        ax.plot([x + width], [mean + yerr_upper[i]], 
                'k-', linewidth=2)
    
    ax.set_xticks(x_pos)
    ax.set_xticklabels(rates, rotation=45, ha='right')
    ax.set_xlabel('Arrival Rate (kHz)')
    ax.set_ylabel('Users Scheduled per Round')
    ax.set_title('Scheduled Users per TTI\n(Statistics from 20 repetitions)')
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')

def plot_summary_table(results, ax):
    """Create a summary statistics table"""
    ax.axis('tight')
    ax.axis('off')
    
    # Prepare summary data
    response_df = results['response_time']
    system_df = results['system_throughput']
    arrival_rates = results['arrival_rates']
    
    # Group by arrival rate
    grouped_response = group_by_arrival_rate(response_df, arrival_rates)
    grouped_system = group_by_arrival_rate(system_df, arrival_rates)
    
    # Create table data
    table_data = []
    headers = ['Arrival Rate (Hz)', 'Avg Response Time (s)', 'System Throughput (Mbps)', 
               'Samples', 'Status']
    
    for rate_key in sorted(grouped_response.keys()):
        # Response time
        response_rows = grouped_response[rate_key]
        response_values = [row['mean'] for row in response_rows]
        avg_response = np.mean(response_values)
        
        # System throughput
        if rate_key in grouped_system:
            system_rows = grouped_system[rate_key]
            throughput_values = [row['system_throughput_mbps'] for row in system_rows]
            avg_throughput = np.mean(throughput_values)
        else:
            avg_throughput = 0
        
        # Determine status
        if avg_response > 1.0:
            status = 'SATURATED'
        elif avg_response > 0.1:
            status = 'High Load'
        else:
            status = 'Normal'
        
        rate_label = f"{rate_key} Hz" if not isinstance(rate_key, tuple) else f"{rate_key[0]}"
        
        table_data.append([
            rate_label,
            f"{avg_response:.6f}",
            f"{avg_throughput:.3f}",
            len(response_rows),
            status
        ])
    
    # Create table
    table = ax.table(cellText=table_data, colLabels=headers,
                     cellLoc='center', loc='center')
    
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 2)
    
    # Style the table
    for i in range(len(headers)):
        table[(0, i)].set_facecolor('#4CAF50')
        table[(0, i)].set_text_props(weight='bold', color='white')
    
    # Color code status column
    for i in range(1, len(table_data) + 1):
        status = table_data[i-1][4]
        if status == 'SATURATED':
            table[(i, 4)].set_facecolor('#ffcccc')
        elif status == 'High Load':
            table[(i, 4)].set_facecolor('#ffffcc')
        else:
            table[(i, 4)].set_facecolor('#ccffcc')

def print_detailed_statistics(results, filepath="detailed_statistics.txt"):
    with open(filepath, 'w') as f:
        def output_line(line):
            print(line)
            f.write(line + '\n')

        output_line("\n" + "="*100)
        output_line("CELLULARROUNDROBIN VALIDATION TEST - DETAILED ANALYSIS")
        output_line("="*100)
        
        # Response Time Statistics
        output_line("\n--- RESPONSE TIME STATISTICS ---")
        response_df = results['response_time']
        arrival_rates = results['arrival_rates']
        grouped = group_by_arrival_rate(response_df, arrival_rates)
        
        for rate_key in sorted(grouped.keys()):
            rows = grouped[rate_key]
            output_line(f"\nArrival Rate: {rate_key} Hz")
            
            # Group by user
            user_data = {}
            for row in rows:
                user_id = row['user_id'] if 'user_id' in row else 0
                if user_id not in user_data:
                    user_data[user_id] = []
                user_data[user_id].append(row['mean'])
            
            for user_id, values in sorted(user_data.items()):
                stats = calculate_statistics(values)
                output_line(f"  User {user_id}:")
                output_line(f"    Mean: {stats['mean']:.6f} s")
                output_line(f"    99% CI: [{stats['ci_lower']:.6f}, {stats['ci_upper']:.6f}]")
                output_line(f"    Samples: {stats['n']}")
                
        
        # System Throughput Statistics
        output_line("\n--- SYSTEM THROUGHPUT STATISTICS ---")
        system_df = results['system_throughput']
        grouped_system = group_by_arrival_rate(system_df, arrival_rates)
        
        for rate_key in sorted(grouped_system.keys()):
            rows = grouped_system[rate_key]
            values = [row['system_throughput_mbps'] for row in rows]
            stats = calculate_statistics(values)
            
            output_line(f"\nArrival Rate: {rate_key} Hz")
            output_line(f"  Mean Throughput: {stats['mean']:.3f} Mbps")
            output_line(f"  99% CI: [{stats['ci_lower']:.3f}, {stats['ci_upper']:.3f}] Mbps")
            output_line(f"  Samples: {stats['n']}")
        
        output_line("\n" + "="*100)
    
    print(f"\nDetailed statistics saved to: {filepath}")

def main():
    """Main analysis function"""
    # Load and process data
    print("Loading data...")
    
    try:
        results = load_and_process_data('../csv_results/validation_test42_scalar.csv')
        
        # Check if we have data
        if results['response_time'].empty:
            print("Error: No response time data found in the CSV file.")
            return
        
        print(f"Found data for {len(results['arrival_rates'])} simulation runs")
        
        # Print detailed statistics
        print_detailed_statistics(results)
        
        # Create comprehensive plots
        fig = create_comprehensive_plots(results)
        
        # Save the comprehensive plot
        output_filename = 'comprehensive_analysis.png'
        plt.savefig(output_filename, dpi=300, bbox_inches='tight')
        print(f"\nComprehensive plot saved as '{output_filename}'")
        
        # Save detailed statistics to CSV files
        results['response_time'].to_csv('response_time_detailed.csv', index=False)
        results['throughput'].to_csv('user_throughput_detailed.csv', index=False)
        results['system_throughput'].to_csv('system_throughput_detailed.csv', index=False)
        results['queue_length'].to_csv('queue_length_detailed.csv', index=False)
        results['resource_utilization'].to_csv('resource_utilization_detailed.csv', index=False)
        results['scheduled_users'].to_csv('scheduled_users_detailed.csv', index=False)
        
        print("\nDetailed statistics saved to CSV files")
        
        # Show plot
        plt.show()
        
    except Exception as e:
        print(f"Error during analysis: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()