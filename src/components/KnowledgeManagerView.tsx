import React, { useState, useEffect, useRef } from 'react';
import {
  BookOpen,
  Upload,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Clock,
  Sparkles,
  Trash2,
  FileText,
  ShieldCheck,
  RefreshCw,
  Plus,
  Layers,
  ChevronRight,
  ExternalLink,
  Award,
  Eye,
  Check,
  Building2,
  Sliders,
  Send,
  Loader2,
  HelpCircle,
} from 'lucide-react';
import {
  Workspace,
  DocumentItem,
  DocumentChunk,
  VerificationReport,
  UIState,
  ToastType,
} from '../types';
import {
  getWorkspaces,
  createWorkspace,
  updateWorkspace,
  getDocuments,
  uploadDocument,
  deleteDocument,
  verifyDocument,
  getVerificationReport,
  publishDocument,
  getDocumentChunks,
} from '../services/api';

interface KnowledgeManagerViewProps {
  currentWorkspaceId: number;
  setCurrentWorkspaceId: (id: number) => void;
  demoState: UIState;
  onToast: (msg: string, type?: ToastType) => void;
}

export const KnowledgeManagerView: React.FC<KnowledgeManagerViewProps> = ({
  currentWorkspaceId,
  setCurrentWorkspaceId,
  demoState,
  onToast,
}) => {
  // State
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [selectedWorkspace, setSelectedWorkspace] = useState<Workspace | null>(null);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [isVerifyingId, setIsVerifyingId] = useState<number | null>(null);

  // Persona edit form state
  const [personaName, setPersonaName] = useState<string>('');
  const [toneOfVoice, setToneOfVoice] = useState<string>('');
  const [businessRules, setBusinessRules] = useState<string>('');
  const [isSavingPersona, setIsSavingPersona] = useState<boolean>(false);

  // Verification Report Modal
  const [verificationModalOpen, setVerificationModalOpen] = useState<boolean>(false);
  const [activeReport, setActiveReport] = useState<VerificationReport | null>(null);
  const [activeDoc, setActiveDoc] = useState<DocumentItem | null>(null);
  const [isPublishing, setIsPublishing] = useState<boolean>(false);

  // Chunk Inspector Modal
  const [chunkModalOpen, setChunkModalOpen] = useState<boolean>(false);
  const [activeChunks, setActiveChunks] = useState<DocumentChunk[]>([]);
  const [chunkDocTitle, setChunkDocTitle] = useState<string>('');

  // New Workspace Modal
  const [newWorkspaceModalOpen, setNewWorkspaceModalOpen] = useState<boolean>(false);
  const [newWsName, setNewWsName] = useState('');
  const [newWsSlug, setNewWsSlug] = useState('');
  const [newWsIndustry, setNewWsIndustry] = useState('');
  const [newWsPersona, setNewWsPersona] = useState('');
  const [newWsTone, setNewWsTone] = useState('');
  const [newWsRules, setNewWsRules] = useState('');

  const fileInputRef = useRef<HTMLInputElement>(null);

  // 1. Initial Load of Workspaces
  useEffect(() => {
    async function loadWorkspaces() {
      setIsLoading(true);
      const wsList = await getWorkspaces(onToast);
      setWorkspaces(wsList);
      if (wsList.length > 0) {
        const found = wsList.find((w) => w.id === currentWorkspaceId) || wsList[0];
        setSelectedWorkspace(found);
        setCurrentWorkspaceId(found.id);
        setPersonaName(found.persona_name);
        setToneOfVoice(found.tone_of_voice);
        setBusinessRules(found.business_rules);
      }
      setIsLoading(false);
    }
    loadWorkspaces();
  }, []);

  // 2. Load Documents when currentWorkspaceId changes
  useEffect(() => {
    if (!selectedWorkspace) return;
    loadDocs(selectedWorkspace.id);
  }, [selectedWorkspace?.id]);

  async function loadDocs(wsId: number) {
    const docs = await getDocuments(wsId, onToast);
    setDocuments(docs);
  }

  function handleSelectWorkspace(wsId: number) {
    const found = workspaces.find((w) => w.id === wsId);
    if (found) {
      setSelectedWorkspace(found);
      setCurrentWorkspaceId(found.id);
      setPersonaName(found.persona_name);
      setToneOfVoice(found.tone_of_voice);
      setBusinessRules(found.business_rules);
    }
  }

  async function handleSavePersona() {
    if (!selectedWorkspace) return;
    setIsSavingPersona(true);
    try {
      const updated = await updateWorkspace(
        selectedWorkspace.id,
        {
          persona_name: personaName,
          tone_of_voice: toneOfVoice,
          business_rules: businessRules,
        },
        onToast
      );
      setSelectedWorkspace(updated);
      setWorkspaces((prev) => prev.map((w) => (w.id === updated.id ? updated : w)));
      onToast('Đã lưu cấu hình Persona và Quy tắc nghiệp vụ thành công!', 'success');
    } catch (e: any) {
      onToast(`Lỗi khi lưu cấu hình: ${e.message}`, 'error');
    } finally {
      setIsSavingPersona(false);
    }
  }

  async function handleFileUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file || !selectedWorkspace) return;

    setIsUploading(true);
    onToast(`Đang tải lên và chia nhỏ tài liệu ${file.name}...`, 'info');
    try {
      const newDoc = await uploadDocument(selectedWorkspace.id, file, onToast);
      setDocuments((prev) => [newDoc, ...prev]);
      onToast(`Tải lên thành công! Đã tạo ${newDoc.chunk_count} đoạn kiến thức.`, 'success');
    } catch (err: any) {
      onToast(`Lỗi tải lên: ${err.message}`, 'error');
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  }

  async function handleDelete(docId: number) {
    if (!confirm('Bạn có chắc chắn muốn xóa tài liệu này và toàn bộ các đoạn vector liên quan?')) return;
    try {
      await deleteDocument(docId, onToast);
      setDocuments((prev) => prev.filter((d) => d.id !== docId));
      onToast('Đã xóa tài liệu an toàn.', 'success');
    } catch (err: any) {
      onToast(`Lỗi xóa tài liệu: ${err.message}`, 'error');
    }
  }

  async function handleVerify(doc: DocumentItem) {
    setIsVerifyingId(doc.id);
    onToast(
      `Đang khởi chạy sát hạch AI 3 bước cho ${doc.filename}... Vui lòng đợi trong giây lát.`,
      'info'
    );
    try {
      const report = await verifyDocument(doc.id, onToast);
      setActiveReport(report);
      setActiveDoc(doc);
      setVerificationModalOpen(true);
      // Reload documents to update status
      if (selectedWorkspace) loadDocs(selectedWorkspace.id);
    } catch (err: any) {
      onToast(`Lỗi trong quá trình sát hạch: ${err.message}`, 'error');
    } finally {
      setIsVerifyingId(null);
    }
  }

  async function handleViewReport(doc: DocumentItem) {
    try {
      const report = await getVerificationReport(doc.id, onToast);
      setActiveReport(report);
      setActiveDoc(doc);
      setVerificationModalOpen(true);
    } catch (err: any) {
      onToast(`Chưa có báo cáo sát hạch cho tài liệu này. Vui lòng bấm 'Sát hạch AI' trước.`, 'warning');
    }
  }

  async function handlePublish() {
    if (!activeDoc) return;
    setIsPublishing(true);
    try {
      await publishDocument(activeDoc.id, onToast);
      onToast(`Tài liệu '${activeDoc.filename}' đã được xuất bản và kích hoạt vào Chatbot RAG!`, 'success');
      setActiveDoc({ ...activeDoc, status: 'published' });
      if (selectedWorkspace) loadDocs(selectedWorkspace.id);
      setVerificationModalOpen(false);
    } catch (err: any) {
      onToast(`Lỗi khi xuất bản: ${err.message}`, 'error');
    } finally {
      setIsPublishing(false);
    }
  }

  async function handleViewChunks(doc: DocumentItem) {
    try {
      setChunkDocTitle(doc.filename);
      const chunks = await getDocumentChunks(doc.id, onToast);
      setActiveChunks(chunks);
      setChunkModalOpen(true);
    } catch (err: any) {
      onToast(`Không thể tải các đoạn trích: ${err.message}`, 'error');
    }
  }

  async function handleCreateWorkspaceSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!newWsName.trim() || !newWsSlug.trim()) {
      onToast('Vui lòng nhập tên và mã slug doanh nghiệp.', 'warning');
      return;
    }
    try {
      const created = await createWorkspace(
        {
          name: newWsName,
          slug: newWsSlug,
          industry: newWsIndustry || 'Chung',
          persona_name: newWsPersona || 'AI Support Assistant',
          tone_of_voice: newWsTone || 'Chuyên nghiệp, thân thiện',
          business_rules: newWsRules || '',
        },
        onToast
      );
      setWorkspaces((prev) => [...prev, created]);
      setSelectedWorkspace(created);
      setCurrentWorkspaceId(created.id);
      setPersonaName(created.persona_name);
      setToneOfVoice(created.tone_of_voice);
      setBusinessRules(created.business_rules);
      setNewWorkspaceModalOpen(false);
      onToast(`Đã tạo thành công doanh nghiệp '${created.name}'!`, 'success');
      // Reset form
      setNewWsName('');
      setNewWsSlug('');
      setNewWsIndustry('');
      setNewWsPersona('');
      setNewWsTone('');
      setNewWsRules('');
    } catch (err: any) {
      onToast(`Lỗi tạo doanh nghiệp: ${err.message}`, 'error');
    }
  }

  return (
    <div className="flex-1 bg-slate-50 overflow-y-auto">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 space-y-6">
        {/* VIEW TITLE & WORKSPACE BAR */}
        <div className="bg-white rounded-2xl border border-slate-200/80 p-5 shadow-xs">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-2.5">
                <div className="p-2 rounded-xl bg-indigo-50 text-indigo-600 border border-indigo-100">
                  <BookOpen className="w-5 h-5" />
                </div>
                <div>
                  <h2 className="text-lg font-bold text-slate-900 tracking-tight">
                    Trung Tâm Quản Trị Tri Thức &amp; Sát Hạch AI (Active Verification Studio)
                  </h2>
                  <p className="text-xs text-slate-500">
                    Nạp tài liệu động (.pdf, .txt, .md), chia đoạn thông minh, và kiểm định chất lượng RAG trước khi công bố.
                  </p>
                </div>
              </div>
            </div>

            {/* Workspace Dropdown & Add Button */}
            <div className="flex items-center gap-2 shrink-0">
              <div className="flex items-center gap-1.5 bg-slate-100 px-3 py-1.5 rounded-xl border border-slate-200">
                <Building2 className="w-4 h-4 text-slate-500" />
                <span className="text-xs font-semibold text-slate-700">Lĩnh vực:</span>
                <select
                  value={selectedWorkspace?.id || 1}
                  onChange={(e) => handleSelectWorkspace(Number(e.target.value))}
                  className="bg-transparent text-xs font-bold text-indigo-700 focus:outline-none cursor-pointer"
                >
                  {workspaces.map((ws) => (
                    <option key={ws.id} value={ws.id}>
                      {ws.name} ({ws.industry})
                    </option>
                  ))}
                </select>
              </div>

              <button
                onClick={() => setNewWorkspaceModalOpen(true)}
                className="flex items-center gap-1 px-3 py-1.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold shadow-xs transition-colors"
              >
                <Plus className="w-3.5 h-3.5" />
                Thêm Doanh Nghiệp
              </button>
            </div>
          </div>
        </div>

        {/* SECTION 1: WORKSPACE PERSONA & BUSINESS RULES CONFIGURATION */}
        {selectedWorkspace && (
          <div className="bg-white rounded-2xl border border-slate-200/80 p-5 shadow-xs space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2">
                <Sliders className="w-4 h-4 text-indigo-600" />
                <h3 className="font-bold text-sm text-slate-900">
                  Cấu Hình Persona &amp; Quy Tắc Nghiệp Vụ: {selectedWorkspace.name}
                </h3>
                <span className="text-[11px] bg-slate-100 text-slate-600 px-2 py-0.5 rounded-full font-medium">
                  Ngành: {selectedWorkspace.industry}
                </span>
              </div>
              <button
                onClick={handleSavePersona}
                disabled={isSavingPersona}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-xs font-semibold transition-all shadow-xs"
              >
                {isSavingPersona ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Check className="w-3.5 h-3.5" />}
                Lưu Cấu Hình
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Tên Persona Bot (Tên Trợ Lý Đại Diện)
                </label>
                <input
                  type="text"
                  value={personaName}
                  onChange={(e) => setPersonaName(e.target.value)}
                  placeholder="Ví dụ: Bác sĩ SmileCare Bot"
                  className="w-full text-xs px-3 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 bg-slate-50/50"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Giọng Điệu Giao Tiếp (Tone of Voice)
                </label>
                <input
                  type="text"
                  value={toneOfVoice}
                  onChange={(e) => setToneOfVoice(e.target.value)}
                  placeholder="Ví dụ: Ân cần, chu đáo, đồng cảm, chuyên môn cao..."
                  className="w-full text-xs px-3 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 bg-slate-50/50"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Quy Tắc Nghiệp Vụ Bắt Buộc (Business Rules &amp; Operational Guardrails)
              </label>
              <textarea
                rows={2}
                value={businessRules}
                onChange={(e) => setBusinessRules(e.target.value)}
                placeholder="Ví dụ: Hướng dẫn chính sách đổi trả 1 đổi 1 trong 30 ngày. Không kê đơn thuốc kháng sinh trực tuyến..."
                className="w-full text-xs px-3 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 bg-slate-50/50"
              />
              <p className="text-[11px] text-slate-400 mt-1">
                Các quy tắc này được Dynamic Prompt Builder tự động ráp vào chỉ dẫn hệ thống của Chatbot và AI Copilot Draft.
              </p>
            </div>
          </div>
        )}

        {/* SECTION 2: DOCUMENT UPLOAD & INGESTION DROPZONE */}
        <div className="bg-white rounded-2xl border border-slate-200/80 p-5 shadow-xs space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Upload className="w-4 h-4 text-indigo-600" />
              <h3 className="font-bold text-sm text-slate-900">Nạp Tài Liệu Kiến Thức Mới</h3>
            </div>
            <span className="text-[11px] text-slate-500 font-medium bg-slate-100 px-2.5 py-1 rounded-full">
              Hỗ trợ: .PDF, .TXT, .MD (Tối đa 15 trang / 10MB)
            </span>
          </div>

          <div
            onClick={() => fileInputRef.current?.click()}
            className="border-2 border-dashed border-indigo-200 hover:border-indigo-400 bg-indigo-50/40 hover:bg-indigo-50/70 rounded-2xl p-6 text-center cursor-pointer transition-all flex flex-col items-center justify-center gap-2"
          >
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileUpload}
              accept=".pdf,.txt,.md"
              className="hidden"
            />
            {isUploading ? (
              <div className="flex items-center gap-2 text-indigo-600 font-semibold text-xs">
                <Loader2 className="w-5 h-5 animate-spin" />
                <span>Đang bóc tách văn bản, chia đoạn và tính vector embedding (Throttled Free-Tier Guard)...</span>
              </div>
            ) : (
              <>
                <div className="w-10 h-10 rounded-full bg-indigo-100 text-indigo-600 flex items-center justify-center shadow-xs">
                  <Upload className="w-5 h-5" />
                </div>
                <div className="text-xs font-semibold text-slate-800">
                  Kéo thả tệp vào đây hoặc <span className="text-indigo-600 underline">chọn từ máy tính</span>
                </div>
                <p className="text-[11px] text-slate-500 max-w-md">
                  Hệ thống tự động chạy thuật toán <strong>Recursive Character Splitter</strong> (600-800 ký tự, overlap 100) và tính vector embedding qua Gemini text-embedding-004.
                </p>
              </>
            )}
          </div>
        </div>

        {/* SECTION 3: DOCUMENTS TABLE & ACTIVE VERIFICATION STATUS */}
        <div className="bg-white rounded-2xl border border-slate-200/80 shadow-xs overflow-hidden">
          <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Layers className="w-4 h-4 text-indigo-600" />
              <h3 className="font-bold text-sm text-slate-900">
                Danh Sách Tài Liệu Trong Kho ({documents.length})
              </h3>
            </div>
            <button
              onClick={() => selectedWorkspace && loadDocs(selectedWorkspace.id)}
              className="flex items-center gap-1 text-xs text-slate-600 hover:text-indigo-600 transition-colors"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              Làm mới
            </button>
          </div>

          {documents.length === 0 ? (
            <div className="p-8 text-center text-slate-400 text-xs">
              Chưa có tài liệu nào trong Doanh nghiệp này. Hãy tải lên tệp .pdf, .txt để bắt đầu!
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200">
                  <tr>
                    <th className="py-3 px-4">Tên tài liệu</th>
                    <th className="py-3 px-4">Định dạng</th>
                    <th className="py-3 px-4">Dung lượng</th>
                    <th className="py-3 px-4">Số đoạn (Chunks)</th>
                    <th className="py-3 px-4">Trạng thái</th>
                    <th className="py-3 px-4 text-right">Thao tác</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {documents.map((doc) => {
                    const isVerifying = isVerifyingId === doc.id;
                    return (
                      <tr key={doc.id} className="hover:bg-slate-50/70 transition-colors">
                        <td className="py-3 px-4 font-semibold text-slate-900 flex items-center gap-2">
                          <FileText className="w-4 h-4 text-indigo-600 shrink-0" />
                          <span className="truncate max-w-xs">{doc.filename}</span>
                        </td>
                        <td className="py-3 px-4 uppercase text-[10px] font-bold text-slate-500">
                          {doc.file_type}
                        </td>
                        <td className="py-3 px-4 text-slate-600">
                          {(doc.file_size / 1024).toFixed(1)} KB
                        </td>
                        <td className="py-3 px-4 text-slate-600">
                          <button
                            onClick={() => handleViewChunks(doc)}
                            className="font-bold text-indigo-600 hover:underline flex items-center gap-1"
                          >
                            <span>{doc.chunk_count} đoạn</span>
                            <Eye className="w-3 h-3" />
                          </button>
                        </td>
                        <td className="py-3 px-4">
                          {doc.status === 'published' && (
                            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                              <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                              Đã xuất bản
                            </span>
                          )}
                          {doc.status === 'verified' && (
                            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-blue-50 text-blue-700 border border-blue-200">
                              <ShieldCheck className="w-3 h-3 text-blue-600" />
                              Đã thẩm định
                            </span>
                          )}
                          {doc.status === 'pending' && (
                            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-amber-50 text-amber-700 border border-amber-200">
                              <Clock className="w-3 h-3 text-amber-600" />
                              Chờ thẩm định
                            </span>
                          )}
                          {doc.status === 'processing' && (
                            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-sky-50 text-sky-700 border border-sky-200">
                              <Loader2 className="w-3 h-3 animate-spin text-sky-600" />
                              Đang sát hạch
                            </span>
                          )}
                          {doc.status === 'failed' && (
                            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-rose-50 text-rose-700 border border-rose-200">
                              <XCircle className="w-3 h-3 text-rose-600" />
                              Chưa đạt
                            </span>
                          )}
                        </td>
                        <td className="py-3 px-4 text-right">
                          <div className="flex items-center justify-end gap-1.5">
                            {doc.status !== 'published' && (
                              <button
                                onClick={() => handleVerify(doc)}
                                disabled={isVerifying}
                                className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-[11px] shadow-xs transition-colors disabled:opacity-50"
                                title="Kích hoạt Active Verification Engine"
                              >
                                {isVerifying ? (
                                  <>
                                    <Loader2 className="w-3 h-3 animate-spin" />
                                    <span>Đang kiểm tra...</span>
                                  </>
                                ) : (
                                  <>
                                    <Sparkles className="w-3 h-3" />
                                    <span>Sát hạch AI</span>
                                  </>
                                )}
                              </button>
                            )}

                            {(doc.status === 'verified' || doc.status === 'published' || doc.status === 'failed') && (
                              <button
                                onClick={() => handleViewReport(doc)}
                                className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-[11px] transition-colors"
                              >
                                <Award className="w-3 h-3 text-indigo-600" />
                                <span>Báo Cáo</span>
                              </button>
                            )}

                            <button
                              onClick={() => handleDelete(doc.id)}
                              className="p-1 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 transition-colors"
                              title="Xóa tài liệu và các vector chunks"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* ----------------------------------------------------------------- */}
      {/* MODAL 1: VERIFICATION STUDIO MODAL (Báo Cáo Thẩm Định & Xuất Bản) */}
      {/* ----------------------------------------------------------------- */}
      {verificationModalOpen && activeReport && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-3xl w-full max-h-[90vh] flex flex-col shadow-2xl overflow-hidden border border-slate-200 animate-in fade-in duration-200">
            {/* Modal Header */}
            <div className="px-6 py-4 bg-gradient-to-r from-indigo-900 via-indigo-800 to-slate-900 text-white flex items-center justify-between shrink-0">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-indigo-500/30 border border-indigo-400/40 flex items-center justify-center">
                  <ShieldCheck className="w-4 h-4 text-indigo-300" />
                </div>
                <div>
                  <h3 className="font-bold text-sm tracking-tight">
                    Báo Cáo Sát Hạch Tri Thức (Active Knowledge Verification)
                  </h3>
                  <p className="text-[11px] text-indigo-200">
                    Tài liệu: {activeDoc?.filename}
                  </p>
                </div>
              </div>
              <button
                onClick={() => setVerificationModalOpen(false)}
                className="text-indigo-200 hover:text-white p-1 rounded-lg hover:bg-white/10"
              >
                ✕
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6 overflow-y-auto space-y-5">
              {/* Faithfulness Score Summary Banner */}
              <div className="bg-slate-50 rounded-2xl p-4 border border-slate-200 flex flex-col sm:flex-row items-center justify-between gap-4">
                <div className="flex items-center gap-3">
                  <div
                    className={`w-14 h-14 rounded-2xl flex flex-col items-center justify-center font-bold text-base border ${
                      activeReport.faithfulness_score >= 0.85
                        ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                        : activeReport.faithfulness_score >= 0.60
                        ? 'bg-amber-50 text-amber-700 border-amber-200'
                        : 'bg-rose-50 text-rose-700 border-rose-200'
                    }`}
                  >
                    <span>{Math.round(activeReport.faithfulness_score * 100)}%</span>
                    <span className="text-[9px] font-semibold uppercase">Điểm</span>
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-slate-900">Độ Trung Thực (Faithfulness Score)</span>
                      <span
                        className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full ${
                          activeReport.status === 'passed'
                            ? 'bg-emerald-100 text-emerald-800'
                            : activeReport.status === 'warning'
                            ? 'bg-amber-100 text-amber-800'
                            : 'bg-rose-100 text-rose-800'
                        }`}
                      >
                        {activeReport.status === 'passed' ? 'PASSED (Đạt Chuẩn)' : activeReport.status === 'warning' ? 'WARNING (Cần Lưu Ý)' : 'FAILED (Không Đạt)'}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-500 mt-0.5">
                      Đối chiếu qua 3 bước: Sinh câu hỏi giả lập ➔ Chạy RAG thử nghiệm song song ➔ AI Judge chấm điểm.
                    </p>
                  </div>
                </div>

                <div className="text-right shrink-0">
                  <span className="text-[11px] text-slate-400 block">Tiêu chuẩn xuất bản:</span>
                  <span className="text-xs font-semibold text-slate-700">Điểm tối thiểu &ge; 85%</span>
                </div>
              </div>

              {/* Items Detail Table */}
              <div className="space-y-3">
                <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                  Chi Tiết Các Câu Hỏi Sát Hạch Thực Tế ({activeReport.items.length})
                </h4>

                <div className="space-y-3">
                  {activeReport.items.map((item, idx) => (
                    <div
                      key={item.id || idx}
                      className="bg-white rounded-xl border border-slate-200 p-4 space-y-2.5 shadow-2xs hover:border-slate-300 transition-colors"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex items-center gap-2">
                          <span className="w-5 h-5 rounded-full bg-indigo-100 text-indigo-700 font-bold flex items-center justify-center text-[10px]">
                            {idx + 1}
                          </span>
                          <span className="font-bold text-xs text-slate-900">
                            {item.question}
                          </span>
                        </div>
                        <span
                          className={`text-[10px] font-bold px-2 py-0.5 rounded-full shrink-0 ${
                            item.status === 'passed'
                              ? 'bg-emerald-100 text-emerald-800'
                              : item.status === 'warning'
                              ? 'bg-amber-100 text-amber-800'
                              : 'bg-rose-100 text-rose-800'
                          }`}
                        >
                          Điểm: {Math.round(item.score * 100)}%
                        </span>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs">
                        <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-100">
                          <span className="text-[10px] font-bold text-slate-400 uppercase block mb-1">
                            Nội dung gốc trong tài liệu (Ground Truth):
                          </span>
                          <p className="text-slate-700 italic">{item.ground_truth}</p>
                        </div>

                        <div className="bg-indigo-50/50 p-2.5 rounded-lg border border-indigo-100">
                          <span className="text-[10px] font-bold text-indigo-500 uppercase block mb-1">
                            Câu trả lời thực tế của Chatbot (RAG Answer):
                          </span>
                          <p className="text-slate-800">{item.rag_answer}</p>
                        </div>
                      </div>

                      {item.reason && (
                        <div className="text-[11px] text-slate-500 flex items-center gap-1.5 pt-1 border-t border-slate-100">
                          <CheckCircle2 className="w-3.5 h-3.5 text-indigo-600 shrink-0" />
                          <span><strong>Nhận xét AI Judge:</strong> {item.reason}</span>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Modal Footer / Publication Gate */}
            <div className="px-6 py-4 bg-slate-50 border-t border-slate-200 flex items-center justify-between shrink-0">
              <button
                onClick={() => setVerificationModalOpen(false)}
                className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 hover:bg-slate-200 transition-colors"
              >
                Đóng Báo Cáo
              </button>

              {activeDoc?.status !== 'published' ? (
                <button
                  onClick={handlePublish}
                  disabled={isPublishing}
                  className="flex items-center gap-2 px-5 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold shadow-md shadow-emerald-200 transition-all disabled:opacity-50"
                >
                  {isPublishing ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>Đang kích hoạt...</span>
                    </>
                  ) : (
                    <>
                      <Check className="w-4 h-4" />
                      <span>Phê Duyệt &amp; Xuất Bản Ra Chatbot</span>
                    </>
                  )}
                </button>
              ) : (
                <div className="flex items-center gap-1.5 text-emerald-700 font-bold text-xs">
                  <CheckCircle2 className="w-4 h-4" />
                  <span>Tài liệu đã được xuất bản và đang phục vụ Chatbot</span>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* --------------------------------------------------------- */}
      {/* MODAL 2: CHUNK INSPECTOR MODAL (Xem Chi Tiết Các Đoạn Vector) */}
      {/* --------------------------------------------------------- */}
      {chunkModalOpen && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-2xl w-full max-h-[85vh] flex flex-col shadow-2xl overflow-hidden border border-slate-200">
            <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
              <div>
                <h3 className="font-bold text-sm text-slate-900">
                  Các Đoạn Vector Chunks ({activeChunks.length})
                </h3>
                <p className="text-[11px] text-slate-500">{chunkDocTitle}</p>
              </div>
              <button
                onClick={() => setChunkModalOpen(false)}
                className="text-slate-400 hover:text-slate-700 p-1"
              >
                ✕
              </button>
            </div>

            <div className="p-6 overflow-y-auto space-y-3">
              {activeChunks.map((chunk, idx) => (
                <div
                  key={chunk.id || idx}
                  className="bg-slate-50 p-3.5 rounded-xl border border-slate-200 text-xs space-y-1.5"
                >
                  <div className="flex items-center justify-between text-slate-500 text-[11px] font-semibold">
                    <span className="text-indigo-600 font-bold">{chunk.title}</span>
                    <span>Trang {chunk.page_number}</span>
                  </div>
                  <p className="text-slate-800 leading-relaxed">{chunk.content}</p>
                </div>
              ))}
            </div>

            <div className="px-6 py-3 bg-slate-50 border-t border-slate-200 text-right">
              <button
                onClick={() => setChunkModalOpen(false)}
                className="px-4 py-1.5 rounded-xl bg-slate-200 hover:bg-slate-300 text-xs font-semibold text-slate-700"
              >
                Đóng
              </button>
            </div>
          </div>
        </div>
      )}

      {/* --------------------------------------------------------- */}
      {/* MODAL 3: THÊM DOANH NGHIỆP / WORKSPACE MỚI */}
      {/* --------------------------------------------------------- */}
      {newWorkspaceModalOpen && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
          <form
            onSubmit={handleCreateWorkspaceSubmit}
            className="bg-white rounded-2xl max-w-lg w-full shadow-2xl overflow-hidden border border-slate-200 animate-in fade-in duration-200"
          >
            <div className="px-6 py-4 bg-indigo-600 text-white flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Building2 className="w-5 h-5" />
                <h3 className="font-bold text-sm">Thêm Doanh Nghiệp / Lĩnh Vực Mới</h3>
              </div>
              <button
                type="button"
                onClick={() => setNewWorkspaceModalOpen(false)}
                className="text-indigo-200 hover:text-white"
              >
                ✕
              </button>
            </div>

            <div className="p-6 space-y-3.5 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">Tên Doanh Nghiệp *</label>
                <input
                  type="text"
                  required
                  value={newWsName}
                  onChange={(e) => setNewWsName(e.target.value)}
                  placeholder="Ví dụ: Bệnh Viện Mắt Ánh Sáng"
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Mã Định Danh (Slug) *</label>
                  <input
                    type="text"
                    required
                    value={newWsSlug}
                    onChange={(e) => setNewWsSlug(e.target.value.toLowerCase().replace(/\s+/g, '-'))}
                    placeholder="ví dụ: benh-vien-mat"
                    className="w-full px-3 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Ngành Nghề</label>
                  <input
                    type="text"
                    value={newWsIndustry}
                    onChange={(e) => setNewWsIndustry(e.target.value)}
                    placeholder="ví dụ: Y tế & Nhãn khoa"
                    className="w-full px-3 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                  />
                </div>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Tên Trợ Lý AI (Persona Name)</label>
                <input
                  type="text"
                  value={newWsPersona}
                  onChange={(e) => setNewWsPersona(e.target.value)}
                  placeholder="Ví dụ: Bác sĩ Ánh Sáng Advisor"
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Giọng Điệu Giao Tiếp</label>
                <input
                  type="text"
                  value={newWsTone}
                  onChange={(e) => setNewWsTone(e.target.value)}
                  placeholder="Ví dụ: Ân cần, từ tốn, chuyên môn y khoa"
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Quy Tắc Nghiệp Vụ Bắt Buộc</label>
                <textarea
                  rows={2}
                  value={newWsRules}
                  onChange={(e) => setNewWsRules(e.target.value)}
                  placeholder="Ví dụ: Báo giá dịch vụ mổ cận Lasik, lịch khám trước phẫu thuật..."
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                />
              </div>
            </div>

            <div className="px-6 py-3.5 bg-slate-50 border-t border-slate-200 flex items-center justify-end gap-2">
              <button
                type="button"
                onClick={() => setNewWorkspaceModalOpen(false)}
                className="px-4 py-1.5 rounded-xl text-xs font-semibold text-slate-600 hover:bg-slate-200 transition-colors"
              >
                Hủy
              </button>
              <button
                type="submit"
                className="px-5 py-1.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold shadow-xs transition-colors"
              >
                Tạo Doanh Nghiệp
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
};
