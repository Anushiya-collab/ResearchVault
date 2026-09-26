import { useEffect, useState } from "react";
import "./App.css";
const API_URL = import.meta.env.VITE_API_URL;

function App() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");
  const [name, setName] = useState("");
const [showRegister, setShowRegister] = useState(false);
  const [loggedIn, setLoggedIn] = useState(false);
  const [workspaces, setWorkspaces] = useState<any[]>([]);
  const [sources, setSources] = useState<any[]>([]);
  const [refetchStatus, setRefetchStatus] = useState<{
  sourceId: number;
  message: string;
  type: "success" | "changed" | "error";
} | null>(null);
  const [claims, setClaims] = useState<any[]>([]);
  const [affectedClaimIds, setAffectedClaimIds] = useState<number[]>([]);
  const [claimDetails, setClaimDetails] = useState<any[]>([]);
  const [expandedEvidence, setExpandedEvidence] = useState<number | null>(null);
  const [selectedWorkspace, setSelectedWorkspace] = useState<any | null>(null);
  const [sourceVersions, setSourceVersions] = useState<any[]>([]);
  const [sourceChanges, setSourceChanges] = useState<any[]>([]);
  const [showCreateForm, setShowCreateForm] = useState(false);
const [newTitle, setNewTitle] = useState("");
const [newQuestion, setNewQuestion] = useState("");
const [importUrl, setImportUrl] = useState("");
const [importMessage, setImportMessage] = useState("");
const [importingUrl, setImportingUrl] = useState(false);
const [pdfFile, setPdfFile] = useState<File | null>(null);
const [pdfMessage, setPdfMessage] = useState("");
const [uploadingPdf, setUploadingPdf] = useState(false);
const [searchQuery, setSearchQuery] = useState("");
const [searchResults, setSearchResults] = useState<any | null>(null);
const [searching, setSearching] = useState(false);
  const handleLogin = async (event: React.FormEvent) => {
    event.preventDefault();

    setMessage("Logging in...");

    try {
      const response = await fetch(`${API_URL}/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          email,
          password,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        setMessage(data.detail || "Login failed");
        return;
      }

      localStorage.setItem("access_token", data.access_token);

      setMessage("");
      setLoggedIn(true);
    } catch (error) {
      setMessage("Could not connect to the backend.");
    }
  };
  const handleRegister = async (event: React.FormEvent) => {
  event.preventDefault();

  setMessage("Registering...");

  try {
    const response = await fetch(`${API_URL}/register`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        name,
        email,
        password,
      }),
    });

    const data = await response.json();

    if (!response.ok) {
      setMessage(data.detail || "Registration failed");
      return;
    }

    setMessage("Registration successful! Please login.");

    setName("");
    setEmail("");
    setPassword("");
    setShowRegister(false);
  } catch (error) {
    setMessage("Could not connect to the backend.");
  }
};

const loadWorkspaces = async () => {
  const token = localStorage.getItem("access_token");

  if (!token) {
    return;
  }

  try {
    const workspaceResponse = await fetch(
      `${API_URL}/workspaces`,
      {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      }
    );

    if (!workspaceResponse.ok) {
      return;
    }

    const workspaceData = await workspaceResponse.json();

    setWorkspaces(workspaceData);

    if (workspaceData.length > 0) {
      const workspaceId = workspaceData[0].id;

      // Load sources
      const sourceResponse = await fetch(
        `${API_URL}/workspaces/${workspaceId}/sources`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (sourceResponse.ok) {
        const sourceData = await sourceResponse.json();
        setSources(sourceData);
      }

      // Load claims
      const claimResponse = await fetch(
        `${API_URL}/workspaces/${workspaceId}/claims`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (claimResponse.ok) {
        const claimData = await claimResponse.json();
        setClaims(claimData);
      }
    }
  } catch (error) {
    console.error("Could not load research data:", error);
  }
};

const handleLogout = () => {
  localStorage.removeItem("access_token");
  setLoggedIn(false);
  setEmail("");
  setPassword("");
  setWorkspaces([]);
  setSources([]);
  setClaims([]);
};
const handleImportUrl = async () => {
  const token = localStorage.getItem("access_token");

  if (!token) {
    setImportMessage("Please log in first.");
    return;
  }

  if (!importUrl.trim()) {
    setImportMessage("Please enter a URL.");
    return;
  }

  if (!selectedWorkspace) {
    setImportMessage("Please select a workspace first.");
    return;
  }

  setImportingUrl(true);
  setImportMessage("");

  try {
    const response = await fetch(
      `${API_URL}/workspaces/${selectedWorkspace.id}/sources/import-url?url=${encodeURIComponent(importUrl)}`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      }
    );

    const data = await response.json();

    if (!response.ok) {
      setImportMessage(
        `✕ ${data.detail || "Could not import URL"}`
      );
      return;
    }

    setImportMessage(
      `✓ URL imported successfully — Version ${data.source_version.version_number}`
    );

    setImportUrl("");

    // Refresh the source list
    const sourcesResponse = await fetch(
      `${API_URL}/workspaces/${selectedWorkspace.id}/sources`,
      {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      }
    );

    if (sourcesResponse.ok) {
      const updatedSources = await sourcesResponse.json();
      setSources(updatedSources);
    }

  } catch (error) {
    console.error("URL import failed:", error);
    setImportMessage("✕ Could not connect to the backend.");
  } finally {
    setImportingUrl(false);
  }
};
const handleSearch = async () => {
  const token = localStorage.getItem("access_token");

  if (!token) {
    return;
  }

  if (!searchQuery.trim()) {
    setSearchResults(null);
    return;
  }

  setSearching(true);

  try {
    const response = await fetch(
     `${API_URL}/search?q=${encodeURIComponent(searchQuery)}`,
      {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      }
    );

    const data = await response.json();

    if (!response.ok) {
      console.error("Search failed:", data);
      return;
    }

    setSearchResults(data);
  } catch (error) {
    console.error("Search error:", error);
  } finally {
    setSearching(false);
  }
};
const handlePdfUpload = async () => {
  if (!pdfFile) {
    setPdfMessage("Please select a PDF file.");
    return;
  }

  if (!selectedWorkspace) {
    setPdfMessage("Please select a workspace first.");
    return;
  }

  setUploadingPdf(true);
  setPdfMessage("");

  try {
    const token = localStorage.getItem("access_token");

    const formData = new FormData();
    formData.append("file", pdfFile);

    const response = await fetch(
      `${API_URL}/workspaces/${selectedWorkspace.id}/sources/import-pdf`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      }
    );

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || "PDF upload failed");
    }

    setPdfMessage(
      `✓ PDF imported successfully — Version ${data.version.version_number}`
    );

    setPdfFile(null);

    const sourcesResponse = await fetch(
  `${API_URL}/workspaces/${selectedWorkspace.id}/sources`,
  {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  }
);

if (sourcesResponse.ok) {
  const updatedSources = await sourcesResponse.json();
  setSources(updatedSources);
}
  } catch (error: any) {
    setPdfMessage(`✗ ${error.message}`);
  } finally {
    setUploadingPdf(false);
  }
};

const handleRefetchSource = async (sourceId: number) => {
  const token = localStorage.getItem("access_token");

  if (!token) {
    return;
  }

  try {
    const response = await fetch(
    `${API_URL}/sources/${sourceId}/refetch`, 
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      }
    );

    const data = await response.json();

    console.log("SOURCE REFETCH RESULT:", data);

    if (!response.ok) {
  setRefetchStatus({
    sourceId,
    message: `✕ ${data.detail || "Could not re-fetch source"}`,
    type: "error",
  });
  return;
}

if (data.status === "unchanged") {
  setRefetchStatus({
    sourceId,
    message: "✓ Source is up to date",
    type: "success",
  });
} else if (data.status === "changed") {
  setRefetchStatus({
    sourceId,
    message: `⚠ Source changed — Version ${data.old_version} → Version ${data.new_version}`,
    type: "changed",
  });
}

    // Refresh the page so the new source version is loaded


  } catch (error) {
    console.error(
      "Could not re-fetch source:",
      error
    );

    setRefetchStatus({
  sourceId,
  message: "✕ Could not re-fetch source",
  type: "error",
});
  }
};

const handleCreateWorkspace = async () => {
  console.log("CREATE WORKSPACE CLICKED");
  const token = localStorage.getItem("access_token");

  if (!token) {
    return;
  }

  if (!newTitle.trim() || !newQuestion.trim()) {
    return;
  }

  try {
    const response = await fetch(
      "${API_URL}/workspaces",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          title: newTitle,
          research_question: newQuestion,
        }),
      }
    );

    if (!response.ok) {
      console.error("Failed to create workspace");
      return;
    }

    const newWorkspace = await response.json();

    setWorkspaces((current) => [
      ...current,
      newWorkspace,
    ]);

    setNewTitle("");
    setNewQuestion("");
    setShowCreateForm(false);

    await loadWorkspaces();
  } catch (error) {
    console.error("Could not create workspace:", error);
  }
};

useEffect(() => {
  if (loggedIn) {
    loadWorkspaces();
  }
}, [loggedIn]);

useEffect(() => {
  if (!selectedWorkspace) {
    return;
  }

  const loadWorkspaceSources = async () => {
    const token = localStorage.getItem("access_token");

    if (!token) {
      return;
    }

    try {
      const response = await fetch(
        `${API_URL}/workspaces/${selectedWorkspace.id}/sources`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (!response.ok) {
        return;
      }

      const data = await response.json();

      setSources(data);

      const allVersions: any[] = [];
      const allChanges: any[] = [];
      setAffectedClaimIds([]);

      for (const source of data) {
        const versionResponse = await fetch(
          `${API_URL}/sources/${source.id}/versions`,
          {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          }
        );

        if (versionResponse.ok) {
          const versionData = await versionResponse.json();

          allVersions.push(
            ...versionData.map((version: any) => ({
              ...version,
              source_id: source.id,
            }))
          );
        }

        const changeResponse = await fetch(
          `${API_URL}/sources/${source.id}/changes`,
          {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          }
        );

        if (changeResponse.ok) {
          const changeData = await changeResponse.json();

          console.log(
            "SOURCE CHANGES LOADED:",
            changeData
          );

          allChanges.push(changeData);
        }
        const affectedResponse = await fetch(
  `${API_URL}/sources/${source.id}/affected-claims`,
  {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  }
);

if (affectedResponse.ok) {
  const affectedData = await affectedResponse.json();

console.log(
  "AFFECTED CLAIM IDs:",
  affectedData.affected_claims.map(
    (claim: any) => claim.id
  )
);

  setAffectedClaimIds((current) => [
    ...current,
    ...affectedData.affected_claims.map(
      (claim: any) => claim.id
    ),
  ]);
}
      }

      setSourceVersions(allVersions);
      setSourceChanges(allChanges);
    } catch (error) {
      console.error(
        "Could not load workspace sources:",
        error
      );
    }
  };

  loadWorkspaceSources();
}, [selectedWorkspace]);


useEffect(() => {
  if (!selectedWorkspace) {
    return;
  }

  const loadWorkspaceClaims = async () => {
    const token = localStorage.getItem("access_token");

    if (!token) {
      return;
    }

    try {
      const response = await fetch(
        `${API_URL}/workspaces/${selectedWorkspace.id}/claims`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (!response.ok) {
        return;
      }

      const data = await response.json();

      setClaims(data);
    } catch (error) {
      console.error(
        "Could not load workspace claims:",
        error
      );
    }
  };

  loadWorkspaceClaims();
}, [selectedWorkspace]);


useEffect(() => {
  if (!claims.length) {
    setClaimDetails([]);
    return;
  }

  const loadClaimDetails = async () => {
    const token = localStorage.getItem("access_token");

    if (!token) {
      return;
    }

    try {
      const allClaimDetails: any[] = [];

      for (const claim of claims) {
        const response = await fetch(
          `${API_URL}/claims/${claim.id}`,
          {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          }
        );

        if (response.ok) {
          const data = await response.json();

          console.log(
            "CLAIM DETAILS LOADED:",
            data
          );

          allClaimDetails.push(data);
        }
      }

      setClaimDetails(allClaimDetails);
    } catch (error) {
      console.error(
        "Could not load claim evidence:",
        error
      );
    }
  };

  loadClaimDetails();
}, [claims]);

  if (loggedIn) {
    return (
      <div className="dashboard">
        <header className="dashboard-header">
          <div>
            <h1>ResearchVault</h1>
            <p>Your personal research workspace</p>
          </div>

          <button
            className="logout-button"
            onClick={handleLogout}
          >
            Logout
          </button>
        </header>
        {selectedWorkspace && (
  <div className="workspace-details">
    <button
      className="back-button"
      onClick={() => setSelectedWorkspace(null)}
    >
      ← Back to Dashboard
    </button>

    <h2>{selectedWorkspace.title}</h2>

    <p>
      {selectedWorkspace.research_question}
    </p>
  </div>
)}

    {selectedWorkspace ? (
      <main className="dashboard-content">
        <div className="workspace-details">
          <button
            className="back-button"
            onClick={() => setSelectedWorkspace(null)}
          >
            ← Back to Dashboard
          </button>

          <h2>{selectedWorkspace.title}</h2>

          <p className="workspace-question">
            {selectedWorkspace.research_question}
          </p>

          <div className="details-section">
            <h3>Workspace Overview</h3>
            <p>
              This workspace contains your research sources,
              evidence, and claims.
            </p>
          </div>

          <div className="details-section">
            <h3>Sources</h3>
            <div className="url-import-box">
  <h4>Import a Web Source</h4>

  <div className="url-import-row">
    <input
      type="url"
      placeholder="https://example.com/article"
      value={importUrl}
      onChange={(e) => setImportUrl(e.target.value)}
    />

    <button
      type="button"
      onClick={handleImportUrl}
      disabled={importingUrl}
    >
      {importingUrl ? "Importing..." : "Import URL"}
    </button>
  </div>

  {importMessage && (
    <p className="import-message">
      {importMessage}
    </p>
  )}
</div>
<div className="pdf-import-box">
  <h4>Import a PDF Source</h4>

  <div className="pdf-import-row">
    <input
      type="file"
      accept=".pdf,application/pdf"
      onChange={(e) => {
        setPdfFile(e.target.files?.[0] || null);
        setPdfMessage("");
      }}
    />

    <button
      type="button"
      onClick={handlePdfUpload}
      disabled={uploadingPdf || !pdfFile}
    >
      {uploadingPdf ? "Uploading..." : "Upload PDF"}
    </button>
  </div>

  {pdfFile && (
    <p className="selected-pdf">
      Selected: {pdfFile.name}
    </p>
  )}

  {pdfMessage && (
    <p className="pdf-message">
      {pdfMessage}
    </p>
  )}
</div>

            {sources.length === 0 ? (
              <p>No sources added yet.</p>
            ) : (
              <div className="source-list">
                {sources.map((source) => (
                  <div className="source-item" key={source.id}>
                    <h4>{source.title}</h4>

                    <p>Type: {source.source_type}</p>

                    {source.url && (
                      <p>URL: {source.url}</p>
                    )}

                    {source.url && (
                      <button
                        type="button"
                        className="refetch-button"
                        onClick={() => handleRefetchSource(source.id)}
                      >
                        🔄 Re-fetch Source
                      </button>
                    )}
                        {refetchStatus &&
                        refetchStatus.sourceId === source.id && (
                            <div
                            className={`refetch-status ${refetchStatus.type}`}
                            >
                            {refetchStatus.message}
                            </div>
                        )}

                   {sourceChanges
  .filter(
    (change) =>
      change.source_id === source.id &&
      (change.old_version ?? change.oldVersion) != null &&
      (change.new_version ?? change.newVersion) != null
  )
  .map((change, index) => (
    <div
      className="source-change-warning"
      key={`${source.id}-${change.old_version ?? change.oldVersion}-${change.new_version ?? change.newVersion}-${index}`}
    >
      <strong>⚠ Source Changed</strong>

      <p>
        Version {change.old_version ?? change.oldVersion}
        {" → "}
        Version {change.new_version ?? change.newVersion}
      </p>
    </div>
  ))}

                    <div className="source-versions">
                      <h5>Versions</h5>

                      {sourceVersions
                        .filter((version) => version.source_id === source.id)
                        .map((version) => (
                          <div
                            className="version-item"
                            key={version.id}
                          >
                            <span>
                              Version {version.version_number}
                            </span>
                            <span>
                              {version.content_length} characters
                            </span>
                          </div>
                        ))}
                    </div>

                    <div className="details-section">
                      <h3>Claims</h3>

                      {claims.length === 0 ? (
                        <p>No claims added yet.</p>
                      ) : (
                        <div className="claim-list">
                          {claims.map((claim) => {
                            const details = claimDetails.find(
                              (item) => item.id === claim.id
                            );

                            return (
                              <div
                                className="claim-item"
                                key={claim.id}
                              >
                                <p className="claim-statement">
                                  {claim.statement}
                                </p>

                                {affectedClaimIds.includes(claim.id) ? (
                                  <span className="claim-status needs-review">
                                    ⚠ Needs Review
                                  </span>
                                ) : (
                                  <span className="claim-status active">
                                    ✓ Active
                                  </span>
                                )}

                                {details?.evidence?.length > 0 && (
                                  <div className="claim-evidence">
                                    <h5>Evidence</h5>

                                    {details.evidence.map((evidence: any) => {
                                      console.log(
                                        "EVIDENCE DATA:",
                                        evidence
                                      );

                                      const version = sourceVersions.find(
                                        (item: any) =>
                                          item.id === evidence.source_version_id
                                      );

                                      const source = sources.find(
                                        (item: any) =>
                                          item.id === version?.source_id
                                      );

                                      return (
                                        <div
                                          className="evidence-item"
                                          key={evidence.id}
                                          onClick={() =>
                                            setExpandedEvidence(
                                              expandedEvidence === evidence.id
                                                ? null
                                                : evidence.id
                                            )
                                          }
                                        >
                                          <p>
                                            "{evidence.exact_text}"
                                          </p>

                                          <div className="evidence-source">
                                            <strong>Source:</strong>{" "}
                                            {source?.title || "Unknown source"}
                                            <br />
                                            <strong>Version:</strong>{" "}
                                            {version
                                              ? `Version ${version.version_number}`
                                              : "Unknown version"}
                                          </div>

                                          {expandedEvidence === evidence.id && (
                                            <div className="provenance-details">
                                              <h6>Provenance Details</h6>

                                              <p>
                                                <strong>Source:</strong>{" "}
                                                {source?.title || "Unknown source"}
                                              </p>

                                              <p>
                                                <strong>Version:</strong>{" "}
                                                {version
                                                  ? `Version ${version.version_number}`
                                                  : "Unknown version"}
                                              </p>

                                              <p>
                                                <strong>Position:</strong>{" "}
                                                {evidence.start_position ?? "N/A"}
                                                {" → "}
                                                {evidence.end_position ?? "N/A"}
                                              </p>

                                              <p>
                                                <strong>Source URL:</strong>{" "}
                                                {source?.url || "N/A"}
                                              </p>

                                              {version?.content_hash && (
                                                <p>
                                                  <strong>Content Hash:</strong>{" "}
                                                  {version.content_hash}
                                                </p>
                                              )}
                                            </div>
                                          )}
                                        </div>
                                      );
                                    })}
                                  </div>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </main>
) : (
        <main className="dashboard-content">
          <h2>Welcome back 👋</h2>

          <p className="dashboard-intro">
            Manage your research, sources, evidence, and claims.
          </p>

          <div className="stats">
            <div className="stat-card">
  <h3>Workspaces</h3>
  <strong>{workspaces.length}</strong>
</div>

           <div className="stat-card">
  <h3>Sources</h3>
  <strong>{sources.length}</strong>
</div>

            <div className="stat-card">
  <h3>Claims</h3>
  <strong>{claims.length}</strong>
</div>
          </div>
          <div className="search-section">
  <h2>Search Research</h2>

  <div className="search-row">
    <input
      type="text"
      placeholder="Search claims and evidence..."
      value={searchQuery}
      onChange={(event) => setSearchQuery(event.target.value)}
      onKeyDown={(event) => {
        if (event.key === "Enter") {
          handleSearch();
        }
      }}
    />

    <button
      type="button"
      onClick={handleSearch}
      disabled={searching}
    >
      {searching ? "Searching..." : "Search"}
    </button>
  </div>

  {searchResults && (
    <div className="search-results">
      <h3>
        Results for "{searchResults.query}"
      </h3>

      <h4>Claims</h4>

      {searchResults.claims.length === 0 ? (
        <p>No matching claims found.</p>
      ) : (
        searchResults.claims.map((claim: any) => (
          <div
            className="search-result-item"
            key={`claim-${claim.id}`}
          >
            <strong>Claim</strong>
            <p>{claim.statement}</p>
          </div>
        ))
      )}

      <h4>Evidence</h4>

      {searchResults.evidence.length === 0 ? (
        <p>No matching evidence found.</p>
      ) : (
        searchResults.evidence.map((evidence: any) => (
          <div
            className="search-result-item"
            key={`evidence-${evidence.id}`}
          >
            <strong>Evidence</strong>
            <p>{evidence.exact_text}</p>
          </div>
        ))
      )}
    </div>
  )}
</div>

          <div className="workspace-section">
            <div className="section-header">
              <h2>My Research</h2>

              <button
  type="button"
  className="create-button"
  onClick={() => setShowCreateForm(true)}
>
  + Create Workspace
</button>
            </div>
            {showCreateForm && (
  <div className="create-form">
    <h3>Create Research Workspace</h3>

    <label>Title</label>

    <input
      type="text"
      placeholder="Enter workspace title"
      value={newTitle}
      onChange={(event) => setNewTitle(event.target.value)}
    />

    <label>Research Question</label>

    <textarea
      placeholder="Enter your research question"
      value={newQuestion}
      onChange={(event) => setNewQuestion(event.target.value)}
    />

    <div className="form-buttons">
      <button
        className="cancel-button"
        onClick={() => setShowCreateForm(false)}
      >
        Cancel
      </button>

      <button
  type="button"
  className="create-button"
  onClick={handleCreateWorkspace}
>
  Create Workspace
</button>
    </div>
  </div>
)}

          <div className="workspace-list">
  {workspaces.length === 0 ? (
    <div className="workspace-card">
      <h3>No workspaces yet</h3>
      <p>Create your first research workspace.</p>
    </div>
  ) : (
    workspaces.map((workspace) => (
     <div
  className="workspace-card"
  key={workspace.id}
  onClick={() => setSelectedWorkspace(workspace)}
>
  <h3>{workspace.title}</h3>

  <p>
    {workspace.research_question}
  </p>

  <div className="claims-preview">
    <h4>Claims</h4>

    {claims.length === 0 ? (
      <p>No claims yet.</p>
    ) : (
      claims.map((claim) => (
        <div className="claim-item" key={claim.id}>
          <p>{claim.statement}</p>

          <span
            className={
              claim.status === "needs_review"
                ? "status-review"
                : "status-active"
            }
          >
            {claim.status === "needs_review"
              ? "⚠ Needs Review"
              : "✓ Active"}
          </span>
        </div>
      ))
    )}
  </div>
</div>
    ))
  )}
</div>
          </div>
        </main>
)}
      </div>
    );

  }

  return (
    <div className="app">
      <div className="login-card">
        <h1>ResearchVault</h1>

        <p className="subtitle">
          Your personal research workspace
        </p>

        {showRegister ? (
  <>
    <h2>Create an account</h2>

    <form onSubmit={handleRegister}>
      <label>Name</label>

      <input
        type="text"
        placeholder="Enter your name"
        value={name}
        onChange={(event) => setName(event.target.value)}
        required
      />

      <label>Email</label>

      <input
        type="email"
        placeholder="Enter your email"
        value={email}
        onChange={(event) => setEmail(event.target.value)}
        required
      />

      <label>Password</label>

      <input
        type="password"
        placeholder="Create a password"
        value={password}
        onChange={(event) => setPassword(event.target.value)}
        required
      />

      <button type="submit">
        Register
      </button>
    </form>

    {message && (
      <p className="message">
        {message}
      </p>
    )}

    <p className="register-text">
      Already have an account?{" "}
      <span
        onClick={() => {
          setShowRegister(false);
          setMessage("");
        }}
        style={{ cursor: "pointer" }}
      >
        Login
      </span>
    </p>
  </>
) : (
  <>
    <h2>Welcome back</h2>

    <form onSubmit={handleLogin}>
      <label>Email</label>

      <input
        type="email"
        placeholder="Enter your email"
        value={email}
        onChange={(event) => setEmail(event.target.value)}
        required
      />

      <label>Password</label>

      <input
        type="password"
        placeholder="Enter your password"
        value={password}
        onChange={(event) => setPassword(event.target.value)}
        required
      />

      <button type="submit">
        Login
      </button>
    </form>

    {message && (
      <p className="message">
        {message}
      </p>
    )}

    <p className="register-text">
      Don't have an account?{" "}
      <span
        onClick={() => {
          setShowRegister(true);
          setMessage("");
        }}
        style={{ cursor: "pointer" }}
      >
        Register
      </span>
    </p>
  </>
)}

      </div>
    </div>
  );
}

export default App;
