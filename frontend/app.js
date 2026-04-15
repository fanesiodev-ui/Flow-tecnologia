/**
 * ContaFácil — Lógica do frontend
 *
 * Responsabilidades:
 *  - Upload de arquivo com drag & drop
 *  - Envio do formulário para a API backend
 *  - Exibição do resultado e download do PDF
 *  - Preview de cores (white label)
 */

const API_BASE = window.location.origin;

// ── Autenticação ──────────────────────────────────────────────────────────────
function getToken() { return localStorage.getItem("cf_token"); }
function getUser()  { try { return JSON.parse(localStorage.getItem("cf_user")) || {}; } catch { return {}; } }

function authHeaders() {
  return { "Authorization": `Bearer ${getToken()}` };
}

function logout() {
  localStorage.removeItem("cf_token");
  localStorage.removeItem("cf_user");
  window.location.href = "/app/login.html";
}

// Redireciona para login se não autenticado
(function verificarAuth() {
  if (!getToken()) window.location.href = "/app/login.html";
  const user = getUser();
  const el = document.getElementById("user-info");
  if (el && user.nome) el.textContent = user.nome + " · " + (user.escritorio || "");
})();

// Arquivo selecionado pelo usuário
let arquivoSelecionado = null;


// ─────────────────────────────────────────────────────────────────
// Upload: Drag & Drop + seleção manual
// ─────────────────────────────────────────────────────────────────

function handleDragOver(e) {
  e.preventDefault();
  document.getElementById("dropZone").classList.add("drag-over");
}

function handleDragLeave(e) {
  document.getElementById("dropZone").classList.remove("drag-over");
}

function handleDrop(e) {
  e.preventDefault();
  document.getElementById("dropZone").classList.remove("drag-over");
  const files = e.dataTransfer.files;
  if (files.length > 0) processarArquivo(files[0]);
}

function handleFileSelect(input) {
  if (input.files.length > 0) processarArquivo(input.files[0]);
}

function processarArquivo(arquivo) {
  const extensoesValidas = [".xlsx", ".xls", ".pdf"];
  const nome = arquivo.name.toLowerCase();
  const valido = extensoesValidas.some(ext => nome.endsWith(ext));

  if (!valido) {
    mostrarErroRapido("Formato inválido. Use Excel (.xlsx) ou PDF.");
    return;
  }

  if (arquivo.size > 10 * 1024 * 1024) {
    mostrarErroRapido("Arquivo muito grande. Máximo: 10 MB.");
    return;
  }

  arquivoSelecionado = arquivo;

  // Atualiza o placeholder com info do arquivo
  document.getElementById("uploadPlaceholder").classList.add("hidden");
  document.getElementById("uploadPreview").classList.remove("hidden");
  document.getElementById("fileIcon").textContent = nome.endsWith(".pdf") ? "📄" : "📊";
  document.getElementById("fileName").textContent = arquivo.name;
  document.getElementById("fileSize").textContent = formatarTamanho(arquivo.size);
}

function limparArquivo(e) {
  e.stopPropagation();
  arquivoSelecionado = null;
  document.getElementById("fileInput").value = "";
  document.getElementById("uploadPlaceholder").classList.remove("hidden");
  document.getElementById("uploadPreview").classList.add("hidden");
}

function formatarTamanho(bytes) {
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
  return (bytes / (1024 * 1024)).toFixed(2) + " MB";
}


// ─────────────────────────────────────────────────────────────────
// Geração de relatório real (com arquivo)
// ─────────────────────────────────────────────────────────────────

async function gerarRelatorio() {
  // Validações
  const empresaNome = document.getElementById("empresaNome").value.trim();
  const periodo = document.getElementById("periodo").value.trim();

  if (!arquivoSelecionado) {
    mostrarErroRapido("Selecione um arquivo Excel ou PDF primeiro.");
    return;
  }
  if (!empresaNome) {
    mostrarErroRapido("Informe o nome da empresa.");
    document.getElementById("empresaNome").focus();
    return;
  }
  if (!periodo) {
    mostrarErroRapido("Informe o período de referência.");
    document.getElementById("periodo").focus();
    return;
  }

  const formData = new FormData();
  formData.append("file", arquivoSelecionado);
  formData.append("empresa_nome", empresaNome);
  formData.append("periodo", periodo);
  await enviarParaAPI("/api/generate-report", formData);
}


// ─────────────────────────────────────────────────────────────────
// Geração de relatório DEMO (sem arquivo)
// ─────────────────────────────────────────────────────────────────

async function gerarDemo() {
  const formData = new FormData();
  formData.append("empresa_nome", document.getElementById("empresaNome").value || "Empresa Modelo LTDA");
  formData.append("periodo", document.getElementById("periodo").value || "Março/2024");
  await enviarParaAPI("/api/demo-report", formData);
}


// ─────────────────────────────────────────────────────────────────
// Envio para a API e tratamento da resposta
// ─────────────────────────────────────────────────────────────────

async function enviarParaAPI(endpoint, formData) {
  setLoadingState(true);
  esconderResultado();

  try {
    // Simula progresso visual
    animarProgresso();

    const response = await fetch(API_BASE + endpoint, {
      method: "POST",
      headers: authHeaders(),
      body: formData,
    });

    const data = await response.json();

    if (response.ok && data.success) {
      mostrarSucesso(data);
    } else {
      mostrarErro(data.detail || data.message || "Erro desconhecido ao gerar o relatório.");
    }
  } catch (err) {
    if (err.name === "TypeError" && err.message.includes("fetch")) {
      mostrarErro(
        "Não foi possível conectar à API. Verifique se o backend está rodando " +
        "(cd backend && uvicorn main:app --reload) e tente novamente."
      );
    } else {
      mostrarErro("Erro inesperado: " + err.message);
    }
  } finally {
    setLoadingState(false);
  }
}


// ─────────────────────────────────────────────────────────────────
// UI: Estados de loading, sucesso e erro
// ─────────────────────────────────────────────────────────────────

function setLoadingState(loading) {
  const btn = document.getElementById("btnGerar");
  const btnText = document.getElementById("btnText");
  const btnIcon = document.getElementById("btnIcon");
  const progress = document.getElementById("progressContainer");

  if (loading) {
    btn.disabled = true;
    btn.classList.add("opacity-70", "cursor-not-allowed");
    btnText.textContent = "Gerando...";
    btnIcon.textContent = "⏳";
    progress.classList.remove("hidden");
  } else {
    btn.disabled = false;
    btn.classList.remove("opacity-70", "cursor-not-allowed");
    btnText.textContent = "Gerar Relatório PDF";
    btnIcon.textContent = "📄";
    progress.classList.add("hidden");
    // Reset progress bar
    document.getElementById("progressBar").style.width = "0%";
  }
}

function animarProgresso() {
  const bar = document.getElementById("progressBar");
  const text = document.getElementById("progressText");

  const etapas = [
    { pct: 20, msg: "Lendo o arquivo..." },
    { pct: 45, msg: "Extraindo dados financeiros..." },
    { pct: 65, msg: "Analisando resultados..." },
    { pct: 85, msg: "Gerando o PDF profissional..." },
    { pct: 95, msg: "Finalizando..." },
  ];

  let i = 0;
  const intervalo = setInterval(() => {
    if (i >= etapas.length) {
      clearInterval(intervalo);
      return;
    }
    bar.style.width = etapas[i].pct + "%";
    text.textContent = etapas[i].msg;
    i++;
  }, 600);
}

function mostrarSucesso(data) {
  const container = document.getElementById("resultContainer");
  const success = document.getElementById("resultSuccess");
  const error = document.getElementById("resultError");

  success.classList.remove("hidden");
  error.classList.add("hidden");
  container.classList.remove("hidden");

  // Mensagem
  document.getElementById("resultMessage").textContent =
    data.message || "Seu relatório está pronto para download.";

  // Link de download (via fetch para incluir o header Authorization)
  const downloadBtn = document.getElementById("downloadBtn");
  downloadBtn.href = "#";
  downloadBtn.onclick = async (e) => {
    e.preventDefault();
    await baixarPDF(API_BASE + data.download_url);
  };

  // Cards de resumo (se houver dados)
  if (data.summary) {
    const s = data.summary;
    document.getElementById("summaryCards").innerHTML = `
      ${criarCardResumo("💰", "Faturamento", formatarBRL(s.faturamento))}
      ${criarCardResumo("📈", "Lucro Líquido", formatarBRL(s.lucro_liquido))}
      ${criarCardResumo("🔍", "Insights", s.total_insights + " encontrados")}
      ${criarCardResumo("🎯", "Recomendações", s.total_recomendacoes + " sugeridas")}
    `;
  } else {
    document.getElementById("summaryCards").innerHTML = "";
  }

  // Scroll suave até o resultado
  container.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function criarCardResumo(icone, label, valor) {
  return `
    <div class="bg-slate-50 rounded-xl p-3 text-center border border-slate-100">
      <div class="text-xl mb-1">${icone}</div>
      <div class="text-xs text-slate-500 mb-0.5">${label}</div>
      <div class="text-sm font-bold text-slate-700">${valor}</div>
    </div>
  `;
}

function mostrarErro(mensagem) {
  const container = document.getElementById("resultContainer");
  const success = document.getElementById("resultSuccess");
  const error = document.getElementById("resultError");

  error.classList.remove("hidden");
  success.classList.add("hidden");
  container.classList.remove("hidden");

  document.getElementById("errorMessage").textContent = mensagem;
  container.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function mostrarErroRapido(mensagem) {
  // Toast simples de erro
  const toast = document.createElement("div");
  toast.className =
    "fixed bottom-6 left-1/2 -translate-x-1/2 bg-red-600 text-white px-5 py-3 rounded-xl shadow-lg text-sm font-medium z-50 fade-in";
  toast.textContent = "⚠️ " + mensagem;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 3500);
}

function esconderResultado() {
  document.getElementById("resultContainer").classList.add("hidden");
}

function novoRelatorio() {
  esconderResultado();
  window.scrollTo({ top: 0, behavior: "smooth" });
}


// ─────────────────────────────────────────────────────────────────
// Utilitários
// ─────────────────────────────────────────────────────────────────

function formatarBRL(valor) {
  if (valor === null || valor === undefined) return "—";
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
  }).format(valor);
}


// ─────────────────────────────────────────────────────────────────
// Histórico de relatórios (banco de dados)
// ─────────────────────────────────────────────────────────────────

async function carregarHistorico() {
  await Promise.all([carregarResumoBanco(), buscarHistorico()]);
}

async function carregarResumoBanco() {
  try {
    const res = await fetch(API_BASE + "/api/historico/resumo", { headers: authHeaders() });
    const data = await res.json();

    document.getElementById("resumoBanco").innerHTML = `
      ${criarCardResumo("📊", "Total de Relatórios", data.total_relatorios)}
      ${criarCardResumo("🏢", "Empresas Atendidas", data.total_empresas)}
    `;
  } catch (e) {
    document.getElementById("resumoBanco").innerHTML = "";
  }
}

async function buscarHistorico() {
  const empresa = document.getElementById("buscaEmpresa").value;
  const url = API_BASE + "/api/historico?limite=50" + (empresa ? `&empresa=${encodeURIComponent(empresa)}` : "");

  try {
    const res = await fetch(url, { headers: authHeaders() });
    const lista = await res.json();
    renderizarHistorico(lista);
  } catch (e) {
    document.getElementById("historicoContainer").innerHTML =
      `<p class="text-red-500 text-sm text-center py-4">Erro ao carregar histórico. Verifique se o backend está rodando.</p>`;
  }
}

function renderizarHistorico(lista) {
  const container = document.getElementById("historicoContainer");

  if (!lista || lista.length === 0) {
    container.innerHTML = `
      <div class="text-center text-slate-400 py-8">
        <div class="text-4xl mb-2">📂</div>
        <p class="text-sm">Nenhum relatório encontrado.</p>
      </div>`;
    return;
  }

  const linhas = lista.map(r => `
    <tr class="border-b border-slate-100 hover:bg-slate-50 transition">
      <td class="py-3 px-4">
        <p class="font-medium text-slate-800 text-sm">${r.empresa_nome}</p>
        <p class="text-slate-400 text-xs">${r.nome_escritorio || "—"}</p>
      </td>
      <td class="py-3 px-4 text-sm text-slate-600">${r.periodo}</td>
      <td class="py-3 px-4 text-sm font-medium text-slate-700">${formatarBRL(r.faturamento)}</td>
      <td class="py-3 px-4 text-sm font-medium ${r.lucro_liquido >= 0 ? "text-green-600" : "text-red-600"}">
        ${formatarBRL(r.lucro_liquido)}
        <span class="text-xs text-slate-400 ml-1">(${r.margem_lucro}%)</span>
      </td>
      <td class="py-3 px-4 text-xs text-slate-400">${r.criado_em}</td>
      <td class="py-3 px-4 text-right">
        <div class="flex items-center justify-end gap-2">
          ${r.tem_pdf ? `
            <button onclick="baixarPDF('${API_BASE}/api/download/${extrairIdDoCaminho(r.arquivo_pdf)}')"
              class="text-blue-600 text-xs font-medium hover:underline">⬇️ PDF</button>
          ` : `<span class="text-slate-300 text-xs">PDF expirado</span>`}
          <button onclick="deletarRelatorio(${r.id})"
            class="text-red-400 text-xs hover:text-red-600">✕</button>
        </div>
      </td>
    </tr>
  `).join("");

  container.innerHTML = `
    <div class="overflow-x-auto">
      <table class="w-full text-left">
        <thead>
          <tr class="border-b-2 border-slate-200">
            <th class="pb-3 px-4 text-xs font-semibold text-slate-500 uppercase">Empresa</th>
            <th class="pb-3 px-4 text-xs font-semibold text-slate-500 uppercase">Período</th>
            <th class="pb-3 px-4 text-xs font-semibold text-slate-500 uppercase">Faturamento</th>
            <th class="pb-3 px-4 text-xs font-semibold text-slate-500 uppercase">Lucro</th>
            <th class="pb-3 px-4 text-xs font-semibold text-slate-500 uppercase">Data</th>
            <th class="pb-3 px-4 text-xs font-semibold text-slate-500 uppercase text-right">Ações</th>
          </tr>
        </thead>
        <tbody>${linhas}</tbody>
      </table>
    </div>`;
}

async function deletarRelatorio(id) {
  if (!confirm("Remover este relatório do histórico?")) return;

  try {
    const res = await fetch(`${API_BASE}/api/relatorio/${id}`, { method: "DELETE", headers: authHeaders() });
    const data = await res.json();
    if (data.success) {
      mostrarErroRapido("✅ Relatório removido!");
      carregarHistorico();
    }
  } catch (e) {
    mostrarErroRapido("Erro ao remover relatório.");
  }
}

function extrairIdDoCaminho(caminho) {
  if (!caminho) return "";
  const nome = caminho.split(/[\\/]/).pop();
  return nome.replace("relatorio_", "").replace(".pdf", "");
}

// ─────────────────────────────────────────────────────────────────
// Download autenticado (envia Bearer token via fetch)
// ─────────────────────────────────────────────────────────────────

async function baixarPDF(url) {
  try {
    const res = await fetch(url, { headers: authHeaders() });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      mostrarErroRapido("Erro ao baixar PDF: " + (err.detail || res.status));
      return;
    }
    const blob = await res.blob();
    const blobUrl = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = blobUrl;
    a.download = "relatorio.pdf";
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(blobUrl);
  } catch (e) {
    mostrarErroRapido("Erro ao baixar PDF: " + e.message);
  }
}

// Carrega o histórico quando a página abre
window.addEventListener("load", () => {
  carregarHistorico();
});
