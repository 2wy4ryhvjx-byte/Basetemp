import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error
import unicodedata

def normalize_text(text, for_filename=False):
    """Remove acentos e padroniza o texto para as colunas"""
    if not isinstance(text, str): return text
    text = "".join(c for c in unicodedata.normalize('NFKD', text) if not unicodedata.combining(c))
    if for_filename: 
        return "".join(c for c in text if c.isalnum() or c in " _-").replace(" ", "_")
    else: 
        return text.lower().replace(" ", "").replace("_", "")

def rename_columns(df):
    """Mapeia os nomes das colunas vindos do Excel/CSV para o padrão do cálculo"""
    COLUMN_MAP = {
        'data': 'Data', 
        'tmin': 'Tmin', 
        'tmín': 'Tmin', 
        'tmax': 'Tmax', 
        'tmáx': 'Tmax', 
        'nf': 'NF'
    }
    df.rename(columns=lambda col: COLUMN_MAP.get(normalize_text(col), col), inplace=True)
    return df

def executar_calculo_tb(df_input, tb_min, tb_max, tb_step):
    """
    O Motor Principal: 
    Calcula a Temperatura Basal (Tb) testando diferentes valores e 
    identificando qual possui o menor Quadrado Médio do Erro (QME).
    """
    df = df_input.copy()
    
    # Cálculo da Temperatura Média
    df['Tmed'] = (df['Tmin'] + df['Tmax']) / 2
    
    # Filtrar apenas as linhas que possuem o Número de Folhas (NF) preenchido
    pheno_df = df.dropna(subset=['NF']).copy()
    
    # Criar colunas de apoio para o relatório final
    df['Dia'] = df['Data'].dt.day
    df['Mês'] = df['Data'].dt.month
    df['Ano'] = df['Data'].dt.year
    
    # Criar um DataFrame de apoio apenas com as temperaturas para acumular a STa
    sta_details_df = df[['Dia', 'Mês', 'Ano', 'Tmin', 'Tmax', 'Tmed']].copy()
    
    results = []
    # Cria a lista de Tb para testar (ex: de 0.0, 0.5, 1.0 ... até 20.0)
    base_temps = np.arange(tb_min, tb_max + tb_step, tb_step)
    
    for tb in base_temps:
        tb_col_name = str(round(tb, 2))
        
        # Cálculo da Soma Térmica diária para esta Tb específica
        df['STd'] = df['Tmed'] - tb
        df.loc[df['STd'] < 0, 'STd'] = 0 # STd não pode ser negativa
        
        # Acumular a soma térmica ao longo do tempo (STa)
        sta_details_df[tb_col_name] = df['STd'].cumsum()
        
        # Preparar dados para a Regressão Linear: STa (X) vs NF (y)
        # Pegamos apenas as datas onde houve medição de NF
        X = sta_details_df.loc[pheno_df.index, tb_col_name].values.reshape(-1, 1)
        y = pheno_df['NF'].values
        
        # Criar e treinar o modelo matemático
        model = LinearRegression().fit(X, y)
        previsoes = model.predict(X)
        qme = mean_squared_error(y, previsoes)
        
        results.append({
            'Temperatura (ºC)': tb, 
            'R2': model.score(X, y), 
            'QME': qme, 
            'Coef_Angular': model.coef_[0], 
            'Intercepto': model.intercept_
        })
        
    # Converter lista de resultados em um DataFrame
    qme_df = pd.DataFrame(results)
    
    # Identificar qual o registro que teve o menor erro (QME)
    best_idx = qme_df['QME'].idxmin()
    best_result = qme_df.loc[best_idx]
    
    return {
        "melhor_resultado": best_result.to_dict(),
        "tabela_erros": qme_df.to_dict(orient="records"),
        "tabela_meteorologica": sta_details_df.to_dict(orient="records")
    }
