/**
 * API Endpoint para servir dados JSON
 * Funciona no Vercel como serverless function
 */

const fs = require('fs');
const path = require('path');

module.exports = (req, res) => {
  // Habilitar CORS
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  res.setHeader('Content-Type', 'application/json');

  // Extrair nome do arquivo da query string
  const { file } = req.query;

  if (!file) {
    return res.status(400).json({
      error: 'Parâmetro "file" é obrigatório',
      example: '/api/data?file=vendas_mensais'
    });
  }

  // Validar nome do arquivo (segurança)
  if (!/^[a-z_]+$/.test(file)) {
    return res.status(400).json({ error: 'Nome de arquivo inválido' });
  }

  const filePath = path.join(__dirname, '..', 'data', `${file}.json`);

  try {
    // Verificar se arquivo existe
    if (!fs.existsSync(filePath)) {
      return res.status(404).json({ error: `Arquivo não encontrado: ${file}.json` });
    }

    // Ler arquivo
    const data = fs.readFileSync(filePath, 'utf8');

    // Parsear JSON para validar
    const parsed = JSON.parse(data);

    // Retornar dados
    res.status(200).json(parsed);

  } catch (error) {
    console.error(`Erro ao servir ${file}.json:`, error);
    return res.status(500).json({
      error: 'Erro ao servir arquivo',
      message: error.message
    });
  }
};
