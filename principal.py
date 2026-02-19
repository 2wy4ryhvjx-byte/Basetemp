import os
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
from io import BytesIO
import stripe

# Importamos as funções que você acabou de salvar no motor.py
from motor import executar_calculo_tb, rename_columns

app = FastAPI()

# Permitir que qualquer navegador acesse sua API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuração do Stripe (Pegará da configuração secreta que faremos no Render)
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

@app.get("/")
def inicio():
    return {"status": "Servidor EstimaTB Ativo", "versao": "1.0"}

@app.post("/analisar")
async def analisar_dados(file: UploadFile = File(...)):
    # 1. Validação simples do formato
    if not file.filename.endswith(('.csv', '.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Formato de arquivo inválido.")

    # 2. Ler o conteúdo do arquivo enviado pelo aluno/professor
    content = await file.read()
    
    try:
        if file.filename.endswith('.csv'):
            df = pd.read_csv(BytesIO(content), sep=None, engine='python')
        else:
            df = pd.read_excel(BytesIO(content))

        # 3. Preparar os dados usando suas funções do motor.py
        df = rename_columns(df)
        df['Data'] = pd.to_datetime(df['Data'], errors='coerce')
        
        # 4. CHAMA O MOTOR CIENTÍFICO
        # Testando de 0 a 20 graus com passo de 0.5 (você pode tornar isso variável depois)
        resultado = executar_calculo_tb(df, 0, 20, 0.5)

        # 5. Lógica de "Métrica de Uso" (Apenas um log por enquanto)
        print(f"Análise realizada com sucesso para o arquivo: {file.filename}")

        return {
            "usuario_status": "free", # Mudaremos para "pro" após o Stripe
            "tb_estimada": resultado['melhor_resultado']['Temperatura (ºC)'],
            "r2": resultado['melhor_resultado']['R2'],
            "qme_minimo": resultado['melhor_resultado']['QME'],
            "mensagem": "Para acessar o relatório completo em Excel, assine o plano Pro."
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar: {str(e)}")

@app.get("/checkout-stripe")
def criar_checkout():
    # Isso gera o link onde o usuário vai pagar de verdade
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card', 'pix'],
            line_items=[{
                'price_data': {
                    'currency': 'brl',
                    'product_data': {'name': 'EstimaTB Pro - Acesso Acadêmico'},
                    'unit_amount': 2990, # R$ 29,90
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url='https://seu-site-final.com/sucesso',
            cancel_url='https://seu-site-final.com/cancelado',
        )
        return {"url": session.url}
    except Exception as e:
        return {"error": str(e)}
