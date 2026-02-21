/**
 * Data Loader para Mercado duBairro
 * Tenta carregar dados de múltiplas fontes
 */

const DATA_SOURCES = [
  // 1. Tentar carregar de /data/ (primeira tentativa)
  { path: '/data/', type: 'json' },
  // 2. Tentar carregar de ./data/ (relativo)
  { path: './data/', type: 'json' },
  // 3. Tentar carregar de /api/data/ (em caso de backend)
  { path: '/api/data/', type: 'api' }
];

async function loadData() {
  const files = ['vendas_mensais', 'vendas_diarias', 'produtos', 'calendario', 'yoy', 'erosao'];
  const DATA = {};
  
  for (const source of DATA_SOURCES) {
    try {
      console.log(`Tentando carregar dados de: ${source.path}`);
      
      const promises = files.map(f =>
        fetch(`${source.path}${f}.json`)
          .then(r => {
            if (!r.ok) {
              throw new Error(`HTTP ${r.status}: ${r.statusText} para ${f}.json`);
            }
            const contentType = r.headers.get('content-type');
            if (!contentType || !contentType.includes('application/json')) {
              throw new Error(`Content-Type incorreto: ${contentType} (esperado: application/json)`);
            }
            return r.json();
          })
      );
      
      const results = await Promise.all(promises);
      files.forEach((f, i) => DATA[f] = results[i]);
      
      console.log(`✅ Dados carregados com sucesso de: ${source.path}`);
      return DATA;
      
    } catch (error) {
      console.warn(`⚠️ Falha ao carregar de ${source.path}:`, error.message);
      continue;
    }
  }
  
  // Se nenhuma fonte funcionou
  throw new Error(
    'Não foi possível carregar os dados de nenhuma fonte.\n' +
    'Verifique se os arquivos JSON existem em /data/\n' +
    'Sources tentadas: ' + DATA_SOURCES.map(s => s.path).join(', ')
  );
}

module.exports = { loadData };
