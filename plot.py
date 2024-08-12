import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os

def adjust_time_values(df):
    for i in range(1, len(df)):
        if df.loc[i, 'Time'] < df.loc[i - 1, 'Time']:
            adjustment = df.loc[i - 1, 'Time'] - df.loc[i, 'Time'] + 100000000000
            df.loc[i:, 'Time'] += adjustment
    return df

def process_file(file_path, save_dir):
    df = pd.read_csv(file_path, header=None, names=['Time', 'X', 'Y', 'Z', 'Heart', 'Swings'])
    df = df[df['Heart'] != 0].reset_index(drop=True)
    df = adjust_time_values(df)
    df['Time'] = df['Time'] - df['Time'].min()
    df['Time'] = pd.to_datetime(df['Time'] // 10**6, unit='ms')
    
    fig, ax = plt.subplots(2, 1, figsize=(10, 8))
    sc1 = ax[0].scatter(df['Time'], df['Swings'], c=df['Heart'], cmap='coolwarm', alpha=0.75)
    fig.colorbar(sc1, ax=ax[0], label='Heart Rate')
    ax[0].set_title('Swing Count over Time')
    # ax[0].set_xlabel('Time')
    ax[0].set_ylabel('Swing Count')
    ax[0].xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
    ax[0].tick_params(axis='x', rotation=45)
    
    grouped = df.groupby('Swings')
    heart_rate_first_row = grouped['Heart'].first()
    sc2 = ax[1].scatter(heart_rate_first_row.index, heart_rate_first_row.values, alpha=0.75)
    ax[1].set_title('Heart Rate over Swing Count')
    ax[1].set_xlabel('Swings')
    ax[1].set_ylabel('Heart Rate')

    file_date = os.path.basename(file_path).replace('-', '/')[:-4]
    plt.figtext(0.01, 0.99, file_date, ha="left", va="top", fontsize=12)

    
    plt.tight_layout()
    
    save_path = os.path.join(save_dir, os.path.basename(file_path).replace('.txt', '.png'))
    plt.savefig(save_path)
    plt.close()

data_dir = 'data'
plots_dir = 'plots'
os.makedirs(plots_dir, exist_ok=True)

for file_name in os.listdir(data_dir):
    file_path = os.path.join(data_dir, file_name)
    plot_file_name = os.path.splitext(file_name)[0] + '.png'
    plot_file_path = os.path.join(plots_dir, plot_file_name)
    
    if os.path.isfile(file_path) and not os.path.exists(plot_file_path):
        process_file(file_path, plots_dir)