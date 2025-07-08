#!/usr/bin/env python3
"""
Warmup and Simulation Time Analysis for CellularRoundRobin
Individual replica plots with convergence analysis
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from collections import defaultdict
import os

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

def load_vector_data(filename):
    """Load and parse vector data from CSV file"""
    # Read CSV
    df = pd.read_csv(filename)
    
    # Pre-filter relevant rows
    vector_df = df[df['type'] == 'vector']
    
    # Initialize data structure
    vector_data = defaultdict(lambda: {
        'inter_arrival': {},
        'system_throughput': {'times': np.array([]), 'values': np.array([])},
        'user_throughput': {},
        'rb_utilization': {'times': np.array([]), 'values': np.array([])},
        'queue_length': {}
    })
    
    run_metadata = {}
    
    # Process vectors
    for _, row in vector_df.iterrows():
        run = row['run']
        
        # Parse run info once
        if run not in run_metadata:
            config_name, repetition = parse_run_info(run)
            run_metadata[run] = {'config': config_name, 'repetition': repetition}
        
        # Parse vectors
        times = parse_vector_string(row['vectime'])
        values = parse_vector_string(row['vecvalue'])
        
        if len(times) == 0 or len(times) != len(values):
            continue
        
        module = row['module']
        name = row['name']
        
        # Route to appropriate storage
        if 'interArrivalTime:vector' in name and 'user[' in module:
            user_id = int(module.split('[')[1].split(']')[0])
            vector_data[run]['inter_arrival'][user_id] = {
                'times': times, 'values': values
            }
        elif 'systemTransmittedBytes:vector' in name and 'scheduler' in module:
            vector_data[run]['system_throughput'] = {
                'times': times, 'values': values
            }
        elif 'bytesTransmitted:vector' in name and 'queue[' in module:
            user_id = int(module.split('[')[1].split(']')[0])
            vector_data[run]['user_throughput'][user_id] = {
                'times': times, 'values': values
            }
        elif 'resourceUtilization:vector' in name:
            vector_data[run]['rb_utilization'] = {
                'times': times, 'values': values
            }
        elif 'queueLength:vector' in name and 'queue[' in module:
            user_id = int(module.split('[')[1].split(']')[0])
            vector_data[run]['queue_length'][user_id] = {
                'times': times, 'values': values
            }
    
    return dict(vector_data), run_metadata

def detect_warmup_stability(times, values, cv_threshold=0.02, min_samples=100, window_fraction=0.5):
    """
    Detect when the cumulative average stabilizes for warmup analysis using coefficient of variation
    
    Parameters:
    - cv_threshold: Maximum coefficient of variation to consider stable (default 0.02 = 2%)
    - min_samples: Minimum number of samples before checking stability
    - window_fraction: Fraction of data to use for stability window (default 0.5 = 50%)
    
    Returns:
    - stability_time: Time when stability is achieved
    - stability_value: The stable value
    """
    n = len(values)
    if n < min_samples:
        return None, None
    
    # Pre-calculate cumulative sum for O(1) average calculation
    cumsum = np.cumsum(values)
    cumavg = [sum/(i+1) for i, sum in enumerate(cumsum)]
    
    # Check stability starting from min_samples
    for i in range(min_samples, n):
        # Look at recent window (minimum 20 samples)
        lookback = max(20, int(window_fraction * i))
        start_idx = i - lookback
        
        window_values = cumavg[start_idx:i]
        window_avg = np.mean(window_values)
        
        # Check coefficient of variation
        if window_avg > 0:
            window_std = np.std(window_values)
            cv = window_std / window_avg
            
            if cv < cv_threshold:
                return times[i], cumavg[i]
    
    return None, None

def calculate_windowed_average(times, values, window_size=1.0, step_size=0.1):
    """
    Windowed average calculation using numpy operations
    """
    if len(times) < 2:
        return np.array([]), np.array([])
    
    # Create time grid
    start_time = 0 # Normally it should be window_size
    end_time = times[-1]
    time_grid = np.arange(start_time, end_time + step_size, step_size)
    
    # Pre-allocate result array
    avg_values = np.zeros(len(time_grid))
    
    # Use searchsorted for efficient window boundary finding
    for i, t in enumerate(time_grid):
        window_start = max(t - window_size, 0)
        
        # Find indices
        start_idx = np.searchsorted(times, window_start, side='left')
        end_idx = np.searchsorted(times, t, side='right')
        
        if end_idx > start_idx:
            avg_values[i] = np.mean(values[start_idx:end_idx])
    
    return time_grid, avg_values

def calculate_cumulative_average(times, values):
    """Calculate cumulative average"""
    if len(values) == 0:
        return np.array([]), np.array([])
    
    cumsum = np.cumsum(values)
    cumavg = cumsum / np.arange(1, len(values) + 1)
    return times, cumavg

def detect_simtime_convergence(times, values, convergence_window=10.0, 
                                        threshold=0.02, min_time=1.0):
    """
    Convergence detection using vectorized operations
    
    Returns:
    - convergence_time: Time when convergence is achieved
    - convergence_value: The converged value
    """
    if len(times) < 10 or times[-1] < min_time:
        return None, None
    
    # Calculate windowed averages
    avg_times, avg_values = calculate_windowed_average(times, values)
    
    if len(avg_times) < 10:
        return None, None
    
    # Find first time after min_time
    start_idx = np.searchsorted(avg_times, min_time)
    
    # Vectorized convergence check
    for i in range(start_idx, len(avg_times)):
        window_start = max(avg_times[i] - convergence_window, 0.0)
        
        # Get window indices
        window_start_idx = np.searchsorted(avg_times, window_start)
        window_values = avg_values[window_start_idx:i+1]
        
        if len(window_values) >= 10:
            mean_val = np.mean(window_values)
            if mean_val > 0:
                cv = np.std(window_values) / mean_val
                if cv < threshold:
                    return avg_times[i], mean_val
    
    return None, None

def create_replica_plots(run_name, run_data, run_metadata, output_dir='plots'):
    """Create individual plots for each replica"""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    config_name = run_metadata[run_name]['config']
    repetition = run_metadata[run_name]['repetition']
    
    convergence_results = {}
    
    # Plot 1: Cumulative mean of inter-arrival time
    if run_data['inter_arrival']:
        fig, ax = plt.subplots(figsize=(12, 8))
        
        for user_id, data in run_data['inter_arrival'].items():
            if len(data['times']) > 0:
                cum_times, cum_values = calculate_cumulative_average(data['times'], data['values'])
                ax.plot(cum_times, cum_values, label=f'User {user_id}', linewidth=2)
                
                # Detect convergence
                conv_time, conv_value = detect_warmup_stability(data['times'], data['values'])
                if conv_time and conv_value:
                    ax.axvline(x=conv_time, color='red', linestyle='--', alpha=0.7)
                    ax.axhline(y=conv_value, color='red', linestyle='--', alpha=0.7)
                    convergence_results[f'inter_arrival_user_{user_id}'] = {
                        'time': conv_time, 'value': conv_value, 'unit': 's'
                    }
        
        ax.set_xlabel('Time (s)')
        ax.set_ylabel('Cumulative Mean Inter-Arrival Time (s)')
        ax.set_title(f'{config_name} Rep{repetition}: Inter-Arrival Time Convergence')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.savefig(f'{output_dir}/{run_name}_inter_arrival.png', dpi=300, bbox_inches='tight')
        plt.tight_layout()
        #plt.show()
        plt.close()
    
    # Plot 2: Windowed mean of queue length
    if run_data['queue_length']:
        fig, ax = plt.subplots(figsize=(12, 8))
        
        for user_id, data in run_data['queue_length'].items():
            if len(data['times']) > 0:
                win_times, win_values = calculate_windowed_average(data['times'], data['values'])
                if len(win_times) > 0:
                    ax.plot(win_times, win_values, label=f'User {user_id}', linewidth=2)
                    
                    # Detect convergence
                    conv_time, conv_value = detect_simtime_convergence(data['times'], data['values'], threshold=0.05)
                    if conv_time and conv_value:
                        ax.axvline(x=conv_time, color='red', linestyle='--', alpha=0.7)
                        ax.axhline(y=conv_value, color='red', linestyle='--', alpha=0.7)
                        convergence_results[f'queue_length_user_{user_id}'] = {
                            'time': conv_time, 'value': conv_value, 'unit': 'packets'
                        }
        
        ax.set_xlabel('Time (s)')
        ax.set_ylabel('Windowed Mean Queue Length')
        ax.set_title(f'{config_name} Rep{repetition}: Queue Length Evolution')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        
        plt.savefig(f'{output_dir}/{run_name}_queue_length.png', dpi=300, bbox_inches='tight')
        plt.tight_layout()
        #plt.show()
        plt.close()
    
    # Plot 3: Windowed mean of user throughput
    if run_data['user_throughput']:
        fig, ax = plt.subplots(figsize=(12, 8))
        
        for user_id, data in run_data['user_throughput'].items():
            if len(data['times']) > 0:
                # Convert to kbps
                throughput_kbps = data['values'] * 8 / 1e3
                win_times, win_values = calculate_windowed_average(data['times'], throughput_kbps)
                if len(win_times) > 0:
                    ax.plot(win_times, win_values, label=f'User {user_id}', linewidth=2)
                    
                    # Detect convergence
                    conv_time, conv_value = detect_simtime_convergence(data['times'], throughput_kbps, threshold=0.05)
                    if conv_time and conv_value:
                        ax.axvline(x=conv_time, color='red', linestyle='--', alpha=0.7)
                        ax.axhline(y=conv_value, color='red', linestyle='--', alpha=0.7)
                        convergence_results[f'user_throughput_user_{user_id}'] = {
                            'time': conv_time, 'value': conv_value, 'unit': 'kbps'
                        }
        
        ax.set_xlabel('Time (s)')
        ax.set_ylabel('Windowed Mean User Throughput (kbit)')
        ax.set_title(f'{config_name} Rep{repetition}: User Throughput Evolution')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.savefig(f'{output_dir}/{run_name}_user_throughput.png', dpi=300, bbox_inches='tight')
        plt.tight_layout()
        #plt.show()
        plt.close()
    
    # Plot 4: Windowed mean of system throughput
    if len(run_data['system_throughput']['times']) > 0:
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # Convert bytes/TTI to Mbps (assuming 1ms TTI)
        throughput_mbps = run_data['system_throughput']['values'] * 8 / 1e6 / 0.001
        win_times, win_values = calculate_windowed_average(
            run_data['system_throughput']['times'], throughput_mbps)
        
        if len(win_times) > 0:
            ax.plot(win_times, win_values, linewidth=2, color='blue', label='System Throughput')
            
            # Detect convergence
            conv_time, conv_value = detect_simtime_convergence(
                run_data['system_throughput']['times'], throughput_mbps)
            if conv_time and conv_value:
                ax.axvline(x=conv_time, color='red', linestyle='--', alpha=0.7, 
                          label=f'Convergence: {conv_time:.1f}s, {conv_value:.2f} Mbps')
                ax.axhline(y=conv_value, color='red', linestyle='--', alpha=0.7)
                convergence_results['system_throughput'] = {
                    'time': conv_time, 'value': conv_value, 'unit': 'Mbps'
                }
        
        ax.set_xlabel('Time (s)')
        ax.set_ylabel('Windowed Mean System Throughput (Mbps)')
        ax.set_title(f'{config_name} Rep{repetition}: System Throughput Evolution')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.savefig(f'{output_dir}/{run_name}_system_throughput.png', dpi=300, bbox_inches='tight')
        plt.tight_layout()
        #plt.show()
        plt.close()
    
    # Plot 5: Windowed mean of resource utilization
    if len(run_data['rb_utilization']['times']) > 0:
        fig, ax = plt.subplots(figsize=(12, 8))
        
        win_times, win_values = calculate_windowed_average(
            run_data['rb_utilization']['times'], run_data['rb_utilization']['values'])
        
        if len(win_times) > 0:
            ax.plot(win_times, win_values, linewidth=2, color='green', label='Resource Utilization')
            
            # Detect convergence
            conv_time, conv_value = detect_simtime_convergence(
                run_data['rb_utilization']['times'], run_data['rb_utilization']['values'],
                convergence_window=5.0)
            if conv_time and conv_value:
                ax.axvline(x=conv_time, color='red', linestyle='--', alpha=0.7,
                          label=f'Convergence: {conv_time:.1f}s, {conv_value:.3f}')
                ax.axhline(y=conv_value, color='red', linestyle='--', alpha=0.7)
                convergence_results['rb_utilization'] = {
                    'time': conv_time, 'value': conv_value, 'unit': 'unit'
                }
        
        ax.set_xlabel('Time (s)')
        ax.set_ylabel('Windowed Mean Resource Utilization')
        ax.set_title(f'{config_name} Rep{repetition}: Resource Utilization Evolution')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.savefig(f'{output_dir}/{run_name}_rb_utilization.png', dpi=300, bbox_inches='tight')
        plt.tight_layout()
        #plt.show()
        plt.close()
    
    return convergence_results

def analyze_warmup_batch(runs_data, cv_threshold=0.02):
    """Analyze warmup for multiple runs in batch using coefficient of variation"""
    results = {}
    
    for run_name, run_data in runs_data.items():
        config_name, repetition = parse_run_info(run_name)
        inter_arrival_data = run_data['inter_arrival']
        
        if not inter_arrival_data:
            continue
        
        stability_points = {}
        stability_values = {}
        max_warmup = 0
        
        for user_id, data in inter_arrival_data.items():
            if len(data['times']) > 0:
                stability_time, stability_value = detect_warmup_stability(
                    data['times'], data['values'], cv_threshold=cv_threshold)
                stability_points[user_id] = stability_time
                stability_values[user_id] = stability_value
                
                if stability_time:
                    max_warmup = max(max_warmup, stability_time)
        
        results[run_name] = {
            'config': config_name,
            'repetition': repetition,
            'user_stability_times': stability_points,
            'user_stability_values': stability_values,
            'recommended_warmup': max_warmup * 1.2 if max_warmup > 0 else None,
            'cv_threshold_used': cv_threshold
        }
    
    return results

def analyze_simtime_batch(runs_data):
    """Analyze simulation time for multiple runs in batch"""
    results = {}
    
    for run_name, run_data in runs_data.items():
        config_name, repetition = parse_run_info(run_name)
        convergence_data = {}
        
        # System throughput
        if len(run_data['system_throughput']['times']) > 0:
            times = run_data['system_throughput']['times']
            # Convert bytes/TTI to Mbps (assuming 1ms TTI)
            throughput_mbps = run_data['system_throughput']['values'] * 8 / 1e6 / 0.001
            
            conv_time, conv_value = detect_simtime_convergence(times, throughput_mbps)
            if conv_time:
                convergence_data['system_throughput'] = {
                    'time': conv_time,
                    'value': conv_value,
                    'unit': 'Mbps'
                }
        
        # Resource utilization
        if len(run_data['rb_utilization']['times']) > 0:
            conv_time, conv_value = detect_simtime_convergence(
                run_data['rb_utilization']['times'],
                run_data['rb_utilization']['values'],
                convergence_window=5.0)
            if conv_time:
                convergence_data['rb_utilization'] = {
                    'time': conv_time,
                    'value': conv_value,
                    'unit': 'ratio'
                }
        
        # User throughput
        user_throughput_data = {}
        for user_id, data in run_data['user_throughput'].items():
            if len(data['times']) > 0:
                # Convert to kbps
                throughput_kbps = data['values'] * 8 / 1e3
                conv_time, conv_value = detect_simtime_convergence(
                    data['times'], throughput_kbps, threshold=0.05)
                if conv_time:
                    user_throughput_data[user_id] = {
                        'time': conv_time,
                        'value': conv_value,
                        'unit': 'kbps'
                    }
        
        if user_throughput_data:
            convergence_data['user_throughput'] = user_throughput_data
        
        # Queue length
        queue_length_data = {}
        for user_id, data in run_data['queue_length'].items():
            if len(data['times']) > 0:
                conv_time, conv_value = detect_simtime_convergence(
                    data['times'], data['values'], threshold=0.05)
                if conv_time:
                    queue_length_data[user_id] = {
                        'time': conv_time,
                        'value': conv_value,
                        'unit': 'packets'
                    }
        
        if queue_length_data:
            convergence_data['queue_length'] = queue_length_data
        
        # Extract convergence times for overall recommendation
        convergence_times = []
        for metric, data in convergence_data.items():
            if metric in ['user_throughput', 'queue_length']:
                user_times = [user_data['time'] for user_data in data.values()]
                if user_times:
                    convergence_times.append(max(user_times))
            else:
                convergence_times.append(data['time'])
        
        # Recommendations
        if convergence_times:
            max_convergence = max(convergence_times)
        else:
            max_convergence = None
        
        results[run_name] = {
            'config': config_name,
            'repetition': repetition,
            'convergence_data': convergence_data,
            'convergence_times': convergence_times,
            'max_convergence': max_convergence
        }
    
    return results

def print_convergence_results(all_convergence_results):
    """Print detailed convergence results for each replica"""
    print("\n" + "="*100)
    print("DETAILED CONVERGENCE RESULTS BY REPLICA")
    print("="*100)
    
    for run_name, results in all_convergence_results.items():
        config_name, repetition = parse_run_info(run_name)
        print(f"\n{config_name} - Repetition {repetition} ({run_name}):")
        print("-" * 60)
        
        if not results:
            print("  No convergence detected")
            continue
        
        # Group by metric type
        for metric_name, data in results.items():
            if 'user_' in metric_name:
                metric_type = metric_name.split('_user_')[0]
                user_id = metric_name.split('_user_')[1]
                print(f"  {metric_type.replace('_', ' ').title()} User {user_id}:")
            else:
                print(f"  {metric_name.replace('_', ' ').title()}:")
            
            print(f"    Convergence Time: {data['time']:.2f} s")
            print(f"    Convergence Value: {data['value']:.4f} {data['unit']}")

def main():
    """Main analysis function"""
    print("Loading vector data...")
    
    # Configuration parameters
    WARMUP_CV_THRESHOLD = 0.02  # 5% coefficient of variation for warmup stability
    
    try:
        # Load data
        vector_data, run_metadata = load_vector_data('../csv_results/warmup_vector_2000_version2.csv')
        
        if not vector_data:
            print("Error: No vector data found in the CSV file.")
            return
        
        print(f"Found data for {len(vector_data)} runs")
        print(f"Using warmup CV threshold: {WARMUP_CV_THRESHOLD}")
        
        # Create individual plots for each replica and collect convergence results
        print("\nCreating individual replica plots...")
        all_convergence_results = {}
        
        for run_name, run_data in vector_data.items():
            print(f"Processing {run_name}...")
            convergence_results = create_replica_plots(run_name, run_data, run_metadata)
            all_convergence_results[run_name] = convergence_results
        
        # Print detailed convergence results
        print_convergence_results(all_convergence_results)
        
        # Batch analysis
        print("\nAnalyzing warmup periods using coefficient of variation...")
        warmup_results = analyze_warmup_batch(vector_data, cv_threshold=WARMUP_CV_THRESHOLD)
        
        print("Analyzing simulation times...")
        simtime_results = analyze_simtime_batch(vector_data)
        
        # Create enhanced summary DataFrame
        summary_data = []
        for run in sorted(set(warmup_results.keys()) | set(simtime_results.keys())):
            warmup = warmup_results.get(run, {})
            simtime = simtime_results.get(run, {})
            
            # Extract convergence values
            system_throughput = 'N/A'
            rb_utilization = 'N/A'
            avg_user_throughput = 'N/A'
            avg_queue_length = 'N/A'
            avg_warmup_value = 'N/A'
            
            # Warmup values
            if 'user_stability_values' in warmup and warmup['user_stability_values']:
                warmup_vals = [v for v in warmup['user_stability_values'].values() if v is not None]
                if warmup_vals:
                    avg_warmup_value = f"{np.mean(warmup_vals):.4f}"
            
            if 'convergence_data' in simtime:
                conv_data = simtime['convergence_data']
                if 'system_throughput' in conv_data:
                    system_throughput = f"{conv_data['system_throughput']['value']:.2f}"
                if 'rb_utilization' in conv_data:
                    rb_utilization = f"{conv_data['rb_utilization']['value']:.3f}"
                if 'user_throughput' in conv_data:
                    user_values = [data['value'] for data in conv_data['user_throughput'].values()]
                    avg_user_throughput = f"{np.mean(user_values):.2f}"
                if 'queue_length' in conv_data:
                    queue_values = [data['value'] for data in conv_data['queue_length'].values()]
                    avg_queue_length = f"{np.mean(queue_values):.2f}"
            
            summary_data.append({
                'Run': run,
                'Config': warmup.get('config', simtime.get('config', 'Unknown')),
                'Repetition': warmup.get('repetition', simtime.get('repetition', 0)),
                'Warmup (s)': warmup.get('recommended_warmup', 'N/A'),
                'Warmup Value (s)': avg_warmup_value,
                'SimTime (s)': simtime.get('max_convergence', 'N/A'),
                'Sys Throughput (Mbps)': system_throughput,
                'RB Utilization': rb_utilization,
                'Avg User Throughput (kbps)': avg_user_throughput,
                'Avg Queue Length': avg_queue_length
            })
        
        summary_df = pd.DataFrame(summary_data)
        
        # Print results
        print("\n" + "="*160)
        print(f"ENHANCED ANALYSIS RESULTS WITH CONVERGENCE VALUES (CV Threshold: {WARMUP_CV_THRESHOLD})")
        print("="*160)
        print(summary_df.to_string(index=False))
        
        # Save results
        summary_df.to_csv('complete_analysis_summary.csv', index=False)
        print("\nSaved: complete_analysis_summary.csv")
        
        # Save convergence results to CSV
        convergence_details = []
        for run_name, results in all_convergence_results.items():
            config_name, repetition = parse_run_info(run_name)
            for metric_name, data in results.items():
                convergence_details.append({
                    'Run': run_name,
                    'Config': config_name,
                    'Repetition': repetition,
                    'Metric': metric_name,
                    'Convergence_Time': data['time'],
                    'Convergence_Value': data['value'],
                    'Unit': data['unit']
                })
        
        if convergence_details:
            convergence_df = pd.DataFrame(convergence_details)
            convergence_df.to_csv('convergence_details.csv', index=False)
            print("Saved: convergence_details.csv")
        
        print(f"\nAll plots saved in 'plots/' directory")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()