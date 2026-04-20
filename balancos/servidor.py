import sys
import webbrowser
import threading
import time
import io
import socket
import subprocess
import logging
import os
import zipfile
import time
import webbrowser
import threading

from flask import Flask, request, send_file, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from io import BytesIO

os.environ["PYTHONUTF8"] = "1"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuração do diretório base
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Configuração das pastas
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'dados')
BALANCO_FOLDER = os.path.join(BASE_DIR, 'balanco')
RELATORIOS_FOLDER = os.path.join(BASE_DIR, 'relatorios')
MODELOS_FOLDER = os.path.join(BASE_DIR, 'Modelos')  # Pasta dos modelos

# Criar pastas
for pasta in [UPLOAD_FOLDER, BALANCO_FOLDER, RELATORIOS_FOLDER, MODELOS_FOLDER]:
    os.makedirs(pasta, exist_ok=True)

print("=== Estrutura das pastas ===")
print(f"\nPasta de Balanços: {BALANCO_FOLDER}")
if os.path.exists(BALANCO_FOLDER):
    for root, dirs, files in os.walk(BALANCO_FOLDER):
        nivel = root.replace(BALANCO_FOLDER, '').count(os.sep)
        indent = ' ' * 2 * nivel
        print(f'{indent}{os.path.basename(root)}/')
        subindent = ' ' * 2 * (nivel + 1)
        for file in files:
            print(f'{subindent}{file}')
else:
    print("   Pasta não encontrada!")

print(f"\nPasta de Relatórios: {RELATORIOS_FOLDER}")
if os.path.exists(RELATORIOS_FOLDER):
    for root, dirs, files in os.walk(RELATORIOS_FOLDER):
        nivel = root.replace(RELATORIOS_FOLDER, '').count(os.sep)
        indent = ' ' * 2 * nivel
        print(f'{indent}{os.path.basename(root)}/')
        subindent = ' ' * 2 * (nivel + 1)
        for file in files:
            print(f'{subindent}{file}')
else:
    print("   Pasta não encontrada!")

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'xlsx', 'docx', 'csv', 'xls', 'doc'}
MODELOS_EXTENSIONS = {'xlsx', 'xls', 'docx', 'doc', 'pdf', 'txt', 'csv'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def allowed_modelo_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in MODELOS_EXTENSIONS

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    response.headers.add('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS')
    return response

@app.route('/')
def index():
    return send_file('index.html')

@app.route('/executar_main', methods=['POST', 'OPTIONS'])
def executar_main():
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.get_json() or {}
        ano = data.get('ano', 2024)
        operacao = data.get('operacao', 3)
        
        print(f"\n{'='*50}")
        print(f"🔍 Executando main.py com:")
        print(f"   Ano: {ano}")
        print(f"   Operação: {operacao}")
        print(f"{'='*50}\n")
        
        main_path = os.path.join(BASE_DIR, 'main.py')
        
        if not os.path.exists(main_path):
            error_msg = f'main.py não encontrado em: {main_path}'
            print(f"❌ {error_msg}")
            return jsonify({'error': error_msg}), 404
        
        try:
            env = os.environ.copy()
            env["PYTHONUTF8"] = "1"
            env["PYTHONIOENCODING"] = "utf-8"

            # Executar o processo e capturar saída
            resultado = subprocess.run(
                [sys.executable, '-u', main_path, '--ano', str(ano), '--operacao', str(operacao)],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                cwd=BASE_DIR,
                env=env,
                timeout=300
            )

            # Separar stdout e stderr
            stdout = resultado.stdout if resultado.stdout else ""
            stderr = resultado.stderr if resultado.stderr else ""
            
            # Filtrar possíveis objetos TextIOWrapper da saída
            # Converter para string segura
            stdout_clean = str(stdout)
            stderr_clean = str(stderr)
            
            if stdout_clean:
                print("📤 STDOUT:")
                print(stdout_clean)
                print("-" * 50)
                
                # Verificar se há objetos TextIOWrapper no stdout
                if "TextIOWrapper" in stdout_clean:
                    print("⚠️ Detectado TextIOWrapper no stdout - será filtrado")
                    # Limpar linhas que contenham TextIOWrapper
                    linhas = stdout_clean.split('\n')
                    linhas_filtradas = [l for l in linhas if 'TextIOWrapper' not in l]
                    stdout_clean = '\n'.join(linhas_filtradas)

            if stderr_clean:
                print("⚠️ STDERR:")
                print(stderr_clean)
                print("-" * 50)
            
            # Verificar se houve erro
            if resultado.returncode == 0:
                return jsonify({
                    'success': f'✅ Relatórios gerados com sucesso! (Ano: {ano})',
                    'output': stdout_clean[:5000]  # Limitar tamanho da resposta
                })
            else:
                # Se houver erro, incluir informações detalhadas
                mensagem_erro = f'❌ Erro ao gerar relatórios (código {resultado.returncode})'
                
                # Tentar extrair mensagem de erro útil
                if stderr_clean:
                    # Pegar as últimas linhas do erro
                    linhas_erro = stderr_clean.split('\n')[-10:]
                    erro_detalhado = '\n'.join(linhas_erro)
                else:
                    erro_detalhado = stdout_clean.split('\n')[-10:] if stdout_clean else []
                    erro_detalhado = '\n'.join(erro_detalhado) if isinstance(erro_detalhado, list) else erro_detalhado
                
                return jsonify({
                    'error': mensagem_erro,
                    'details': erro_detalhado[:1000],  # Limitar tamanho
                    'output': stdout_clean[:2000]
                }), 500
                
        except subprocess.TimeoutExpired:
            return jsonify({'error': '⏰ Tempo limite excedido (5 minutos).'}), 500
        except Exception as e:
            error_msg = f'Erro ao executar: {str(e)}'
            print(f"❌ {error_msg}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': error_msg}), 500
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Erro: {str(e)}'}), 500

#LISTAGEM DE FICHEIROS
@app.route('/listar_ficheiros', methods=['GET', 'OPTIONS'])
def listar_ficheiros():
    if request.method == 'OPTIONS':
        return '', 200
    
    def get_files(pasta):
        files = []
        if os.path.exists(pasta):
            for root, dirs, files_in_dir in os.walk(pasta):
                for file in files_in_dir:
                    filepath = os.path.join(root, file)
                    # Obter caminho relativo usando / (barras normais) em vez de \
                    rel_path = os.path.relpath(filepath, pasta)
                    # Substituir barras invertidas por barras normais para compatibilidade web
                    rel_path = rel_path.replace('\\', '/')
                    
                    files.append({
                        'nome': rel_path,  # Agora vai ser "2022/Relatório_Lisboa.xlsx"
                        'nome_apenas': file,
                        'caminho_completo': filepath,
                        'tamanho': os.path.getsize(filepath),
                        'modificado': os.path.getmtime(filepath)
                    })
        files.sort(key=lambda x: x['modificado'], reverse=True)
        return files
    
    print(f"\n📂 Listando ficheiros:")
    print(f"   Dados: {UPLOAD_FOLDER}")
    print(f"   Balanco: {BALANCO_FOLDER}")
    print(f"   Relatorios: {RELATORIOS_FOLDER}")
    
    dados = get_files(UPLOAD_FOLDER)
    balanco = get_files(BALANCO_FOLDER)
    relatorios = get_files(RELATORIOS_FOLDER)
    
    print(f"   Total encontrado: {len(dados)} dados, {len(balanco)} balanços, {len(relatorios)} relatórios")
    
    return jsonify({
        'dados': dados,
        'balanco': balanco,
        'relatorios': relatorios
    })

@app.route('/listar_modelos', methods=['GET', 'OPTIONS'])
def listar_modelos():
    """Listar todos os arquivos na pasta Modelos"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        if not os.path.exists(MODELOS_FOLDER):
            return jsonify({'error': 'Pasta de modelos não encontrada'}), 404
        
        arquivos = []
        for root, dirs, files in os.walk(MODELOS_FOLDER):
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, MODELOS_FOLDER)
                arquivos.append({
                    'nome': rel_path,
                    'caminho': file_path,
                    'tamanho': os.path.getsize(file_path),
                    'modificado': os.path.getmtime(file_path),
                    'extensao': os.path.splitext(file)[1].lower()
                })
        
        arquivos.sort(key=lambda x: x['modificado'], reverse=True)
        
        return jsonify({
            'success': True,
            'arquivos': arquivos,
            'total': len(arquivos)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@app.route('/listar_dados_com_pastas', methods=['GET', 'OPTIONS'])
def listar_dados_com_pastas():
    """Listar arquivos e pastas na pasta de dados com estrutura hierárquica"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        pasta_atual = request.args.get('pasta', '')
        caminho_completo = os.path.join(UPLOAD_FOLDER, pasta_atual)
        
        if not os.path.exists(caminho_completo):
            return jsonify({'error': 'Pasta não encontrada'}), 404
        
        itens = []
        
        # Listar pastas
        for item in os.listdir(caminho_completo):
            item_path = os.path.join(caminho_completo, item)
            if os.path.isdir(item_path):
                itens.append({
                    'tipo': 'pasta',
                    'nome': item,
                    'caminho': os.path.join(pasta_atual, item).replace('\\', '/') if pasta_atual else item,
                    'modificado': os.path.getmtime(item_path)
                })
        
        # Listar arquivos
        for item in os.listdir(caminho_completo):
            item_path = os.path.join(caminho_completo, item)
            if os.path.isfile(item_path):
                itens.append({
                    'tipo': 'arquivo',
                    'nome': item,
                    'caminho': os.path.join(pasta_atual, item).replace('\\', '/') if pasta_atual else item,
                    'tamanho': os.path.getsize(item_path),
                    'modificado': os.path.getmtime(item_path)
                })
        
        # Ordenar: pastas primeiro, depois arquivos
        itens.sort(key=lambda x: (x['tipo'] != 'pasta', x['nome'].lower()))
        
        return jsonify({
            'success': True,
            'pasta_atual': pasta_atual,
            'itens': itens,
            'caminho_completo': caminho_completo
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/listar_anos_disponiveis', methods=['GET', 'OPTIONS'])
def listar_anos_disponiveis():
    """Listar todos os anos disponíveis nas pastas dados e relatorios"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        anos = set()
        
        # Procurar pastas numéricas em dados
        if os.path.exists(UPLOAD_FOLDER):
            for item in os.listdir(UPLOAD_FOLDER):
                item_path = os.path.join(UPLOAD_FOLDER, item)
                if os.path.isdir(item_path) and item.isdigit():
                    anos.add(item)
        
        # Procurar pastas numéricas em relatorios
        if os.path.exists(RELATORIOS_FOLDER):
            for item in os.listdir(RELATORIOS_FOLDER):
                item_path = os.path.join(RELATORIOS_FOLDER, item)
                if os.path.isdir(item_path) and item.isdigit():
                    anos.add(item)
        
        # Procurar anos em balanços (formato BA_Nome_2024.docx)
        if os.path.exists(BALANCO_FOLDER):
            for root, dirs, files in os.walk(BALANCO_FOLDER):
                for file in files:
                    # Extrair ano de nomes como BA_Regiao_2024.docx
                    import re
                    match = re.search(r'_(\d{4})\.', file)
                    if match:
                        anos.add(match.group(1))
        
        return jsonify({
            'success': True,
            'anos': sorted(list(anos), reverse=True)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
# UPLOAD
@app.route('/upload_modelo', methods=['POST', 'OPTIONS'])
def upload_modelo():
    """Upload de novos modelos para a pasta Modelos"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'Nenhum ficheiro enviado'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'Nome de ficheiro vazio'}), 400
        
        if file and allowed_modelo_file(file.filename):
            # Preservar nome original, apenas remover caracteres proibidos
            filename = file.filename
            forbidden_chars = '<>:"/\\|?*'
            filename = ''.join(c for c in filename if c not in forbidden_chars)
            filename = os.path.basename(filename)
            
            filepath = os.path.join(MODELOS_FOLDER, filename)
            
            if os.path.exists(filepath):
                return jsonify({'error': f'Já existe um modelo com o nome "{filename}"'}), 400
            
            file.save(filepath)
            
            return jsonify({
                'success': True,
                'message': f'✅ Modelo "{filename}" carregado com sucesso!',
                'filename': filename
            })
        else:
            return jsonify({'error': f'Tipo de ficheiro não permitido. Use: {", ".join(MODELOS_EXTENSIONS)}'}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@app.route('/upload', methods=['POST', 'OPTIONS'])
def upload_file():
    if request.method == 'OPTIONS':
        return '', 200
    
    if 'file' not in request.files:
        return jsonify({'error': 'Nenhum ficheiro enviado'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Nome vazio'}), 400
    
    if file and allowed_file(file.filename):
        # Preservar nome original, apenas remover caracteres proibidos
        filename = file.filename
        forbidden_chars = '<>:"/\\|?*'
        filename = ''.join(c for c in filename if c not in forbidden_chars)
        filename = os.path.basename(filename)
        
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        return jsonify({'success': f'✅ {filename} carregado'})

@app.route('/upload_para_pasta', methods=['POST', 'OPTIONS'])
def upload_para_pasta():
    """Upload de ficheiros para uma pasta específica"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        pasta_destino = request.form.get('pasta_destino', '')
        
        if 'file' not in request.files:
            return jsonify({'error': 'Nenhum ficheiro enviado'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'Nome vazio'}), 400
        
        if file and allowed_file(file.filename):
            # NÃO usar secure_filename para preservar o nome original
            filename = file.filename
            
            # Apenas remover caracteres realmente perigosos para o sistema de arquivos
            # Mas manter espaços, acentos, etc.
            forbidden_chars = '<>:"/\\|?*'
            filename = ''.join(c for c in filename if c not in forbidden_chars)
            
            # Remover caminhos de diretório (caso alguém tente fazer path traversal)
            filename = os.path.basename(filename)
            
            # Construir caminho completo
            caminho_completo = os.path.join(UPLOAD_FOLDER, pasta_destino)
            os.makedirs(caminho_completo, exist_ok=True)
            
            filepath = os.path.join(caminho_completo, filename)
            
            # Evitar sobrescrever
            if os.path.exists(filepath):
                nome, ext = os.path.splitext(filename)
                contador = 1
                while os.path.exists(filepath):
                    filename = f"{nome}_{contador}{ext}"
                    filepath = os.path.join(caminho_completo, filename)
                    contador += 1
            
            file.save(filepath)
            
            return jsonify({
                'success': True,
                'message': f'✅ {filename} carregado com sucesso!',
                'filename': filename,
                'caminho': os.path.join(pasta_destino, filename).replace('\\', '/')
            })
        
        return jsonify({'error': 'Tipo de ficheiro não permitido'}), 400
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    

# APAGAR FICHEIROS
@app.route('/apagar_modelo/<path:filename>', methods=['DELETE', 'OPTIONS'])
def apagar_modelo(filename):
    """Apagar um modelo da pasta Modelos"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        from urllib.parse import unquote
        filename = unquote(filename)
        
        filepath = os.path.join(MODELOS_FOLDER, filename)
        
        if not os.path.exists(filepath):
            return jsonify({'error': 'Modelo não encontrado'}), 404
        
        real_path = os.path.realpath(filepath)
        modelos_path = os.path.realpath(MODELOS_FOLDER)
        if not real_path.startswith(modelos_path):
            return jsonify({'error': 'Acesso negado'}), 403
        
        os.remove(filepath)
        
        return jsonify({
            'success': True,
            'message': f'🗑️ Modelo "{filename}" apagado com sucesso!'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/apagar/<tipo>/<path:filename>', methods=['DELETE', 'OPTIONS'])
def apagar_file_individual(tipo, filename):
    from urllib.parse import unquote
    import os
    
    filename = unquote(filename)
    
    # Log para debug
    print(f"\n🔍 Tentando apagar arquivo:")
    print(f"   Tipo: {tipo}")
    print(f"   Filename recebido: {filename}")
    
    # Mapeamento dos tipos para as pastas
    pasta_map = {
        'balanco': BALANCO_FOLDER,
        'relatorios': RELATORIOS_FOLDER,
        'dados': UPLOAD_FOLDER
    }
    
    pasta = pasta_map.get(tipo)
    if not pasta:
        print(f"❌ Tipo inválido: {tipo}")
        return jsonify({'error': 'Tipo inválido'}), 400
    
    print(f"   Pasta base: {pasta}")
    
    # Normalizar o caminho (substituir / por \ no Windows)
    filename_normalizado = filename.replace('/', os.sep)
    filepath = os.path.join(pasta, filename_normalizado)
    print(f"   Caminho completo: {filepath}")
    
    # Verificar se o arquivo existe exatamente no caminho
    if os.path.exists(filepath) and os.path.isfile(filepath):
        try:
            os.remove(filepath)
            print(f"✅ Arquivo apagado: {filepath}")
            
            # Verificar se a pasta pai ficou vazia e remover se necessário
            pasta_pai = os.path.dirname(filepath)
            if pasta_pai != pasta and not os.listdir(pasta_pai):
                try:
                    os.rmdir(pasta_pai)
                    print(f"🗑️ Pasta vazia removida: {pasta_pai}")
                except Exception as e:
                    print(f"   Não foi possível remover pasta: {e}")
            
            return jsonify({'success': f'🗑️ {filename} apagado'})
        except Exception as e:
            print(f"❌ Erro ao apagar: {str(e)}")
            return jsonify({'error': f'Erro ao apagar: {str(e)}'}), 500
    
    # Se não encontrou, tentar buscar por nome do arquivo (ignorando caminho)
    print(f"\n⚠️ Arquivo não encontrado no caminho exato. Procurando recursivamente...")
    
    nome_buscado = os.path.basename(filename_normalizado)
    print(f"   Procurando por nome: {nome_buscado}")
    
    arquivos_encontrados = []
    for root, dirs, files in os.walk(pasta):
        for file in files:
            if file == nome_buscado:
                arquivo_completo = os.path.join(root, file)
                arquivos_encontrados.append(arquivo_completo)
                print(f"   ✅ Encontrado: {arquivo_completo}")
    
    if arquivos_encontrados:
        # Se encontrou múltiplos arquivos com o mesmo nome, perguntar qual apagar
        if len(arquivos_encontrados) > 1:
            print(f"   ⚠️ Encontrados {len(arquivos_encontrados)} arquivos com o mesmo nome:")
            for i, arq in enumerate(arquivos_encontrados):
                print(f"      {i+1}. {arq}")
            # Por enquanto, apagar o primeiro encontrado
            arquivo_apagar = arquivos_encontrados[0]
            print(f"   Apagando o primeiro: {arquivo_apagar}")
        else:
            arquivo_apagar = arquivos_encontrados[0]
        
        try:
            os.remove(arquivo_apagar)
            print(f"✅ Arquivo apagado: {arquivo_apagar}")
            
            # Verificar se a pasta pai ficou vazia
            pasta_pai = os.path.dirname(arquivo_apagar)
            if pasta_pai != pasta and not os.listdir(pasta_pai):
                try:
                    os.rmdir(pasta_pai)
                    print(f"🗑️ Pasta vazia removida: {pasta_pai}")
                except:
                    pass
            
            return jsonify({'success': f'🗑️ {nome_buscado} apagado'})
        except Exception as e:
            print(f"❌ Erro ao apagar: {str(e)}")
            return jsonify({'error': f'Erro ao apagar: {str(e)}'}), 500
    
    # Se não encontrou, listar os arquivos para debug
    print(f"\n❌ Arquivo não encontrado: {nome_buscado}")
    print("   Arquivos disponíveis (primeiros 10):")
    todos_arquivos = []
    for root, dirs, files in os.walk(pasta):
        for file in files:
            todos_arquivos.append(os.path.join(root, file))
    
    for i, arq in enumerate(todos_arquivos[:10]):
        print(f"      {i+1}. {os.path.basename(arq)} (em: {os.path.dirname(arq)})")
    
    return jsonify({'error': f'Ficheiro não encontrado: {filename}'}), 404

# Rota para apagar todos os arquivos de uma pasta
@app.route('/apagar_todos/<tipo>', methods=['DELETE', 'OPTIONS'])
def apagar_todos_arquivos(tipo):
    """Apagar todos os arquivos de uma pasta específica (balanco ou relatorios)"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        # Mapeamento dos tipos para as pastas
        pasta_map = {
            'balanco': BALANCO_FOLDER,
            'relatorios': RELATORIOS_FOLDER
        }
        
        if tipo not in pasta_map:
            return jsonify({'error': 'Tipo inválido. Use "balanco" ou "relatorios"'}), 400
        
        pasta = pasta_map[tipo]
        
        if not os.path.exists(pasta):
            return jsonify({'error': f'Pasta {tipo} não encontrada'}), 404
        
        # Listar todos os arquivos na pasta
        arquivos_apagados = []
        erros = []
        
        for root, dirs, files in os.walk(pasta):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    os.remove(file_path)
                    arquivos_apagados.append(os.path.join(os.path.relpath(root, pasta), file))
                except Exception as e:
                    erros.append(f"{file}: {str(e)}")
        
        # Remover também subdiretórios vazios
        for root, dirs, files in os.walk(pasta, topdown=False):
            for dir_name in dirs:
                dir_path = os.path.join(root, dir_name)
                try:
                    if not os.listdir(dir_path):  # Se o diretório estiver vazio
                        os.rmdir(dir_path)
                except:
                    pass
        
        if arquivos_apagados:
            mensagem = f'✅ Foram apagados {len(arquivos_apagados)} ficheiros da pasta {tipo}.'
            if erros:
                mensagem += f' ⚠️ Erros: {", ".join(erros)}'
            
            return jsonify({
                'success': True,
                'message': mensagem,
                'apagados': len(arquivos_apagados),
                'erros': erros
            })
        else:
            return jsonify({
                'success': True,
                'message': f'ℹ️ A pasta {tipo} já estava vazia.',
                'apagados': 0
            })
        
    except Exception as e:
        logger.error(f"Erro ao apagar todos os arquivos da pasta {tipo}: {str(e)}")
        return jsonify({'error': f'Erro ao apagar ficheiros: {str(e)}'}), 500

@app.route('/apagar_pasta', methods=['DELETE', 'OPTIONS'])
def apagar_pasta():
    """Apagar uma pasta inteira (e todo seu conteúdo)"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.get_json()
        nome_pasta = data.get('nome_pasta', '')
        pasta_atual = data.get('pasta_atual', '')
        
        if not nome_pasta:
            return jsonify({'error': 'Nome da pasta não especificado'}), 400
        
        # Construir caminho completo
        if pasta_atual:
            caminho_completo = os.path.join(UPLOAD_FOLDER, pasta_atual, nome_pasta)
        else:
            caminho_completo = os.path.join(UPLOAD_FOLDER, nome_pasta)
        
        print(f"\n🗑️ Tentando apagar pasta:")
        print(f"   Nome: {nome_pasta}")
        print(f"   Pasta atual: {pasta_atual}")
        print(f"   Caminho completo: {caminho_completo}")
        
        # Verificar se a pasta existe
        if not os.path.exists(caminho_completo):
            return jsonify({'error': f'Pasta não encontrada: {nome_pasta}'}), 404
        
        # Verificar se é realmente uma pasta
        if not os.path.isdir(caminho_completo):
            return jsonify({'error': f'{nome_pasta} não é uma pasta'}), 400
        
        # Contar quantos itens serão apagados
        total_itens = 0
        total_arquivos = 0
        for root, dirs, files in os.walk(caminho_completo):
            total_itens += len(dirs) + len(files)
            total_arquivos += len(files)
        
        # Tentar apagar a pasta e todo seu conteúdo
        import shutil
        shutil.rmtree(caminho_completo)
        
        # Verificar se foi apagada
        if not os.path.exists(caminho_completo):
            print(f"✅ Pasta apagada: {caminho_completo}")
            return jsonify({
                'success': True,
                'message': f'🗑️ Pasta "{nome_pasta}" apagada com sucesso!',
                'detalhes': f'Foram apagados {total_itens} itens ({total_arquivos} arquivos)'
            })
        else:
            return jsonify({'error': 'Falha ao apagar pasta'}), 500
        
    except PermissionError:
        print(f"❌ Permissão negada ao tentar apagar: {caminho_completo}")
        return jsonify({'error': 'Permissão negada. Verifique se a pasta não está aberta em outro programa.'}), 403
    except Exception as e:
        print(f"❌ Erro ao apagar pasta: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Erro ao apagar pasta: {str(e)}'}), 500

@app.route('/apagar_item', methods=['DELETE', 'OPTIONS'])
def apagar_item():
    """Apagar um item (arquivo ou pasta) da pasta de dados"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.get_json()
        caminho_relativo = data.get('caminho', '')
        tipo = data.get('tipo', 'arquivo')
        
        if not caminho_relativo:
            return jsonify({'error': 'Caminho não especificado'}), 400
        
        # Construir caminho completo
        caminho_completo = os.path.join(UPLOAD_FOLDER, caminho_relativo)
        
        print(f"\n🗑️ Tentando apagar {tipo}:")
        print(f"   Caminho relativo: {caminho_relativo}")
        print(f"   Caminho completo: {caminho_completo}")
        
        # Verificar se o item existe
        if not os.path.exists(caminho_completo):
            return jsonify({'error': f'{tipo.capitalize()} não encontrado: {caminho_relativo}'}), 404
        
        # Apagar pasta ou arquivo
        if tipo == 'pasta':
            import shutil
            # Contar itens antes de apagar
            total_itens = 0
            total_arquivos = 0
            for root, dirs, files in os.walk(caminho_completo):
                total_itens += len(dirs) + len(files)
                total_arquivos += len(files)
            
            shutil.rmtree(caminho_completo)
            
            print(f"✅ Pasta apagada: {caminho_completo}")
            return jsonify({
                'success': True,
                'message': f'🗑️ Pasta "{os.path.basename(caminho_relativo)}" apagada com sucesso!',
                'detalhes': f'Foram apagados {total_itens} itens ({total_arquivos} arquivos)'
            })
        else:
            # Apagar arquivo
            os.remove(caminho_completo)
            print(f"✅ Arquivo apagado: {caminho_completo}")
            
            # Verificar se a pasta pai ficou vazia
            pasta_pai = os.path.dirname(caminho_completo)
            if pasta_pai != UPLOAD_FOLDER and not os.listdir(pasta_pai):
                try:
                    os.rmdir(pasta_pai)
                    print(f"🗑️ Pasta vazia removida: {pasta_pai}")
                except Exception as e:
                    print(f"   Não foi possível remover pasta: {e}")
            
            return jsonify({
                'success': True,
                'message': f'🗑️ Ficheiro "{os.path.basename(caminho_relativo)}" apagado com sucesso!'
            })
        
    except PermissionError:
        print(f"❌ Permissão negada ao tentar apagar: {caminho_completo}")
        return jsonify({'error': 'Permissão negada. Verifique se o item não está aberto em outro programa.'}), 403
    except Exception as e:
        print(f"❌ Erro ao apagar: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Erro ao apagar: {str(e)}'}), 500

# DOWNLOAD DE FICHEIROS
@app.route('/download_modelo/<path:filename>', methods=['GET'])
def download_modelo(filename):
    """Download de um modelo específico"""
    try:
        from urllib.parse import unquote
        filename = unquote(filename)
        
        filepath = os.path.join(MODELOS_FOLDER, filename)
        
        if not os.path.exists(filepath):
            return jsonify({'error': 'Modelo não encontrado'}), 404
        
        return send_file(
            filepath,
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download_modelos', methods=['GET'])
def download_modelos():
    """Download da pasta Modelos completa em ZIP"""
    try:
        if not os.path.exists(MODELOS_FOLDER):
            return jsonify({'error': 'Pasta de modelos não encontrada'}), 404
        
        arquivos = []
        for root, dirs, files in os.walk(MODELOS_FOLDER):
            for file in files:
                arquivos.append(os.path.join(root, file))
        
        if not arquivos:
            return jsonify({'error': 'A pasta Modelos está vazia'}), 404
        
        memory_file = BytesIO()
        
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(MODELOS_FOLDER):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, BASE_DIR)
                    zipf.write(file_path, arcname)
        
        memory_file.seek(0)
        
        return send_file(
            memory_file,
            mimetype='application/zip',
            as_attachment=True,
            download_name='modelos.zip'
        )
        
    except Exception as e:
        return jsonify({'error': f'Erro ao criar ZIP: {str(e)}'}), 500

@app.route('/download_pasta/<tipo>', methods=['GET'])
def download_pasta(tipo):
    """Download da pasta completa (balanco ou relatorios) em ZIP"""
    try:
        # Mapeamento dos tipos para as pastas
        pasta_map = {
            'balanco': BALANCO_FOLDER,
            'relatorios': RELATORIOS_FOLDER
        }
        
        if tipo not in pasta_map:
            return jsonify({'error': 'Tipo inválido. Use "balanco" ou "relatorios"'}), 400
        
        pasta = pasta_map[tipo]
        
        if not os.path.exists(pasta):
            return jsonify({'error': f'Pasta {tipo} não encontrada'}), 404
        
        # Listar todos os arquivos na pasta
        arquivos = []
        for root, dirs, files in os.walk(pasta):
            for file in files:
                arquivos.append(os.path.join(root, file))
        
        if not arquivos:
            return jsonify({'error': f'A pasta {tipo} está vazia'}), 404
        
        # Criar arquivo ZIP em memória
        memory_file = BytesIO()
        
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(pasta):
                for file in files:
                    file_path = os.path.join(root, file)
                    # O caminho dentro do ZIP será relativo à pasta base
                    arcname = os.path.relpath(file_path, BASE_DIR)
                    zipf.write(file_path, arcname)
        
        memory_file.seek(0)
        
        return send_file(
            memory_file,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f'{tipo}.zip'
        )
        
    except Exception as e:
        logger.error(f"Erro ao criar ZIP da pasta {tipo}: {str(e)}")
        return jsonify({'error': f'Erro ao criar ZIP: {str(e)}'}), 500

@app.route('/download/<tipo>/<path:filename>')  # <-- adicione "path:"
def download_file(tipo, filename):
    pasta_map = {'balanco': BALANCO_FOLDER, 'relatorios': RELATORIOS_FOLDER, 'dados': UPLOAD_FOLDER}
    pasta = pasta_map.get(tipo)
    if not pasta:
        return jsonify({'error': 'Tipo inválido'}), 400
    
    # filename já pode conter "2024/documento.pdf"
    filepath = os.path.join(pasta, filename)
    
    # IMPORTANTE: segurança para evitar path traversal
    filepath = os.path.abspath(filepath)
    if not filepath.startswith(os.path.abspath(pasta)):
        return jsonify({'error': 'Acesso negado'}), 403
    
    if os.path.exists(filepath) and os.path.isfile(filepath):
        return send_file(filepath, as_attachment=True, download_name=os.path.basename(filename))
    return jsonify({'error': 'Ficheiro não encontrado'}), 404

#CRIAR
@app.route('/criar_pasta', methods=['POST', 'OPTIONS'])
def criar_pasta():
    """Criar uma nova pasta dentro da pasta de dados"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.get_json()
        nome_pasta = data.get('nome_pasta', '').strip()
        pasta_atual = data.get('pasta_atual', '')
        
        if not nome_pasta:
            return jsonify({'error': 'Nome da pasta não pode estar vazio'}), 400
        
        # Validar se contém apenas números
        if not nome_pasta.isdigit():
            return jsonify({'error': 'O nome da pasta deve conter apenas números'}), 400
        
        # Remover caracteres inválidos (embora já tenha validado, manter por segurança)
        nome_pasta = "".join(c for c in nome_pasta if c.isdigit()).strip()
        
        if not nome_pasta:
            return jsonify({'error': 'Nome da pasta inválido'}), 400
        
        caminho_completo = os.path.join(UPLOAD_FOLDER, pasta_atual, nome_pasta)
        
        if os.path.exists(caminho_completo):
            return jsonify({'error': 'Já existe uma pasta com este nome'}), 400
        
        os.makedirs(caminho_completo)
        
        return jsonify({
            'success': True,
            'message': f'✅ Pasta "{nome_pasta}" criada com sucesso!',
            'caminho': os.path.join(pasta_atual, nome_pasta).replace('\\', '/')
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/criar_pasta_ano', methods=['POST', 'OPTIONS'])
def criar_pasta_ano():
    """Criar pasta com nome numérico (ano) nas pastas dados e relatorios"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.get_json()
        ano = str(data.get('ano', ''))
        criar_em_dados = data.get('dados', True)
        criar_em_relatorios = data.get('relatorios', True)
        
        # Validar se é um número
        if not ano or not ano.isdigit():
            return jsonify({'error': 'O ano deve conter apenas números'}), 400
        
        resultados = {}
        
        # Criar pasta em dados se solicitado
        if criar_em_dados:
            pasta_dados = os.path.join(UPLOAD_FOLDER, ano)
            if not os.path.exists(pasta_dados):
                os.makedirs(pasta_dados)
                resultados['dados'] = f'✅ Pasta "{ano}" criada em dados'
            else:
                resultados['dados'] = f'ℹ️ Pasta "{ano}" já existe em dados'
        
        # Criar pasta em relatorios se solicitado
        if criar_em_relatorios:
            pasta_relatorios = os.path.join(RELATORIOS_FOLDER, ano)
            if not os.path.exists(pasta_relatorios):
                os.makedirs(pasta_relatorios)
                resultados['relatorios'] = f'✅ Pasta "{ano}" criada em relatorios'
            else:
                resultados['relatorios'] = f'ℹ️ Pasta "{ano}" já existe em relatorios'
        
        return jsonify({
            'success': True,
            'message': f'Pastas do ano {ano} verificadas/criadas',
            'detalhes': resultados
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

#MOVER
@app.route('/mover_para_pasta_ano', methods=['POST', 'OPTIONS'])
def mover_para_pasta_ano():
    """Mover ficheiros para a pasta do ano correspondente"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.get_json()
        ano = str(data.get('ano', ''))
        tipo = data.get('tipo', 'relatorios')  # 'relatorios' ou 'dados'
        
        if not ano or not ano.isdigit():
            return jsonify({'error': 'Ano inválido'}), 400
        
        # Definir pasta de origem e destino
        if tipo == 'relatorios':
            pasta_base = RELATORIOS_FOLDER
            destino = os.path.join(RELATORIOS_FOLDER, ano)
        elif tipo == 'dados':
            pasta_base = UPLOAD_FOLDER
            destino = os.path.join(UPLOAD_FOLDER, ano)
        else:
            return jsonify({'error': 'Tipo inválido'}), 400
        
        # Criar pasta de destino se não existir
        os.makedirs(destino, exist_ok=True)
        
        moved_files = []
        
        # Mover ficheiros que contêm o ano no nome
        if os.path.exists(pasta_base):
            for item in os.listdir(pasta_base):
                item_path = os.path.join(pasta_base, item)
                
                # Verificar se é um ficheiro e se contém o ano no nome
                if os.path.isfile(item_path):
                    if ano in item:
                        destino_path = os.path.join(destino, item)
                        import shutil
                        shutil.move(item_path, destino_path)
                        moved_files.append(item)
        
        return jsonify({
            'success': True,
            'message': f'Movidos {len(moved_files)} ficheiros para pasta {ano}',
            'movidos': moved_files
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def abrir_browser():
    """Abrir o navegador automaticamente após o servidor iniciar"""
    
    time.sleep(1.5)
    webbrowser.open('http://localhost:5000')

if __name__ == '__main__':
    print("\n" + "="*50)
    print("🚀 Servidor de Gestão de Relatórios")
    print("="*50)
    print(f"📁 Pasta do projeto: {BASE_DIR}")
    print(f"📁 Pasta de modelos: {MODELOS_FOLDER}")
    print(f"🌐 Aceda em: http://localhost:5000")
    print("="*50)
    print("⚠️  Mantenha esta janela aberta enquanto usar o sistema")
    print("="*50)
    print("\n💡 O browser vai abrir automaticamente...\n")
    
    threading.Thread(target=abrir_browser, daemon=True).start()
    app.run(host='localhost', port=5000, debug=False, use_reloader=False)