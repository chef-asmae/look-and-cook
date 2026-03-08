import { useEffect, useMemo, useState } from "react";

function formatSize(sizeBytes) {
  if (sizeBytes < 1024) return `${sizeBytes} B`;
  if (sizeBytes < 1024 * 1024) return `${(sizeBytes / 1024).toFixed(1)} KB`;
  return `${(sizeBytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(isoDateTime) {
  if (!isoDateTime) return "-";
  const parsed = new Date(isoDateTime);
  if (Number.isNaN(parsed.getTime())) return isoDateTime;
  return parsed.toLocaleString();
}

function usePathname() {
  const [pathname, setPathname] = useState(window.location.pathname);

  useEffect(() => {
    const onPopState = () => setPathname(window.location.pathname);
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  function navigate(path) {
    if (path === window.location.pathname) return;
    window.history.pushState({}, "", path);
    setPathname(path);
  }

  return { pathname, navigate };
}

function UploadsPage({ navigate }) {
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [uploadRecords, setUploadRecords] = useState([]);
  const [latestResults, setLatestResults] = useState([]);
  const [uploadDir, setUploadDir] = useState("D:\\data");
  const [status, setStatus] = useState("Ready");
  const [error, setError] = useState("");
  const [isUploading, setIsUploading] = useState(false);

  const totalSize = useMemo(
    () => selectedFiles.reduce((sum, file) => sum + file.size, 0),
    [selectedFiles]
  );

  async function fetchUploadedFiles() {
    try {
      const response = await fetch("/api/uploads");
      if (!response.ok) throw new Error(`Failed to load uploads: ${response.status}`);
      const data = await response.json();
      setUploadDir(data.upload_dir ?? "D:\\data");
      setUploadRecords(data.records ?? []);
    } catch (err) {
      setError(err.message || "Could not load uploaded files.");
    }
  }

  useEffect(() => {
    fetchUploadedFiles();
  }, []);

  function onFileChange(event) {
    const files = Array.from(event.target.files ?? []);
    setSelectedFiles(files);
    setError("");
    setLatestResults([]);
    if (files.length === 0) {
      setStatus("No files selected");
      return;
    }
    const invalidFiles = files.filter((file) => {
      const name = file.name.toLowerCase();
      return !(name.endsWith(".pdf") || name.endsWith(".epub"));
    });
    if (invalidFiles.length > 0) {
      setError("Only PDF and EPUB files are supported for recipe extraction.");
      setStatus("Please select PDF or EPUB files only");
      return;
    }
    setStatus(`Selected ${files.length} file(s)`);
  }

  async function uploadSelectedFiles(event) {
    event.preventDefault();
    if (selectedFiles.length === 0) {
      setStatus("Please select at least one file");
      return;
    }

    setIsUploading(true);
    setError("");
    setStatus("Uploading...");

    try {
      const formData = new FormData();
      selectedFiles.forEach((file) => formData.append("files", file));
      const response = await fetch("/api/uploads", { method: "POST", body: formData });
      if (!response.ok) throw new Error(`Upload failed with status ${response.status}`);
      const data = await response.json();
      const count = data.files?.length ?? 0;
      setLatestResults(data.files ?? []);
      setStatus(`Upload complete: ${count} file(s) processed`);
      setSelectedFiles([]);
      await fetchUploadedFiles();
    } catch (err) {
      setError(err.message || "Upload failed.");
      setStatus("Upload failed");
    } finally {
      setIsUploading(false);
    }
  }

  return (
    <>
      <h1>Cookbook Uploads</h1>
      <p className="hint">
        Upload PDF or EPUB files from desktop or phone. Files are stored in <code>{uploadDir}</code>.
      </p>

      <form className="upload-form" onSubmit={uploadSelectedFiles}>
        <input type="file" accept=".pdf,.epub,application/pdf,application/epub+zip" multiple onChange={onFileChange} />
        <button type="submit" disabled={isUploading}>
          {isUploading ? "Uploading..." : "Upload Files"}
        </button>
      </form>

      <p className="status">{status}</p>
      {selectedFiles.length > 0 && (
        <p className="hint">
          {selectedFiles.length} selected, total size {formatSize(totalSize)}
        </p>
      )}
      {error && <p className="error">{error}</p>}

      <section className="uploaded-files">
        <h2>Latest Analysis</h2>
        {latestResults.length === 0 ? (
          <p className="hint">Upload a PDF or EPUB to view recipe extraction results.</p>
        ) : (
          <ul>
            {latestResults.map((file) => (
              <li key={file.stored_name}>
                <strong>{file.original_name}</strong>: {file.recipe_count} recipe(s) detected.
                <br />
                <span className="hint">{file.notes}</span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="uploaded-files">
        <h2>Recent Upload Index</h2>
        {uploadRecords.length === 0 ? (
          <p className="hint">No uploads yet.</p>
        ) : (
          <ul>
            {uploadRecords.slice(0, 20).map((record) => (
              <li key={record.id}>
                <strong>{record.file_path.split(/[\\/]/).pop()}</strong> ({formatSize(record.size_bytes)})
                <br />
                Uploaded: {formatDate(record.uploaded_at)} | Recipes: {record.recipe_count}
                <br />
                <span className="hint">{record.notes}</span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <div className="actions">
        <button type="button" onClick={() => navigate("/recipes")}>
          Open Recipes
        </button>
      </div>
    </>
  );
}

function RecipesPage({ navigate }) {
  const [query, setQuery] = useState("");
  const [recipes, setRecipes] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  async function loadRecipes(searchTerm) {
    setLoading(true);
    setError("");
    try {
      const params = new URLSearchParams();
      if (searchTerm.trim()) params.set("q", searchTerm.trim());
      params.set("limit", "200");
      const response = await fetch(`/api/recipes?${params.toString()}`);
      if (!response.ok) throw new Error(`Failed to load recipes: ${response.status}`);
      const data = await response.json();
      setRecipes(data.recipes ?? []);
    } catch (err) {
      setError(err.message || "Failed to load recipes.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadRecipes("");
  }, []);

  function onSearchSubmit(event) {
    event.preventDefault();
    loadRecipes(query);
  }

  return (
    <>
      <h1>Recipes</h1>
      <form className="upload-form" onSubmit={onSearchSubmit}>
        <input
          type="text"
          value={query}
          placeholder="Search by recipe title or book name"
          onChange={(event) => setQuery(event.target.value)}
        />
        <button type="submit">Search</button>
      </form>

      {loading && <p className="hint">Loading recipes...</p>}
      {error && <p className="error">{error}</p>}

      <section className="uploaded-files">
        <h2>Results ({recipes.length})</h2>
        {recipes.length === 0 && !loading ? (
          <p className="hint">No recipes found.</p>
        ) : (
          <ul>
            {recipes.map((recipe) => (
              <li key={recipe.id}>
                <button className="link-button" type="button" onClick={() => navigate(`/recipes/${recipe.id}`)}>
                  {recipe.title}
                </button>
                <br />
                <span className="hint">
                  {recipe.book_name} | Page {recipe.page_number}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <div className="actions">
        <button type="button" onClick={() => navigate("/")}>
          Back To Uploads
        </button>
      </div>
    </>
  );
}

function BooksPage({ navigate }) {
  const [books, setBooks] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadBooks() {
      setLoading(true);
      setError("");
      try {
        const response = await fetch("/api/books?limit=500");
        if (!response.ok) throw new Error(`Failed to load books: ${response.status}`);
        const data = await response.json();
        setBooks(data.books ?? []);
      } catch (err) {
        setError(err.message || "Failed to load books.");
      } finally {
        setLoading(false);
      }
    }
    loadBooks();
  }, []);

  return (
    <>
      <h1>Books</h1>
      {loading && <p className="hint">Loading books...</p>}
      {error && <p className="error">{error}</p>}

      <section className="uploaded-files">
        <h2>Uploaded Books ({books.length})</h2>
        {books.length === 0 && !loading ? (
          <p className="hint">No books found.</p>
        ) : (
          <ul>
            {books.map((book) => (
              <li key={book.upload_id}>
                <button className="link-button" type="button" onClick={() => navigate(`/books/${book.upload_id}`)}>
                  {book.book_title || book.file_path.split(/[\\/]/).pop()}
                </button>
                <br />
                <span className="hint">
                  Title: {book.book_title || "Unknown"}
                  <br />
                  Author: {book.book_author || "Unknown"} | Uploaded: {formatDate(book.uploaded_at)} | Recipes:{" "}
                  {book.recipe_count}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </>
  );
}

function BookDetailPage({ uploadId, navigate }) {
  const [book, setBook] = useState(null);
  const [recipes, setRecipes] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadBook() {
      setLoading(true);
      setError("");
      try {
        const response = await fetch(`/api/books/${uploadId}/recipes`);
        if (!response.ok) throw new Error(`Failed to load book: ${response.status}`);
        const data = await response.json();
        setBook(data.book ?? null);
        setRecipes(data.recipes ?? []);
      } catch (err) {
        setError(err.message || "Failed to load book.");
      } finally {
        setLoading(false);
      }
    }
    loadBook();
  }, [uploadId]);

  return (
    <>
      <h1>Book Recipes</h1>
      {loading && <p className="hint">Loading book recipes...</p>}
      {error && <p className="error">{error}</p>}

      {book && (
        <section className="uploaded-files">
          <h2>{book.book_title || book.file_path.split(/[\\/]/).pop()}</h2>
          <p className="hint">
            <strong>Author:</strong> {book.book_author || "Unknown"}
            <br />
            <strong>Date Uploaded:</strong> {formatDate(book.uploaded_at)}
          </p>
          <h3>Recipes ({recipes.length})</h3>
          {recipes.length === 0 ? (
            <p className="hint">No recipes found for this book.</p>
          ) : (
            <ul>
              {recipes.map((recipe) => (
                <li key={recipe.id}>
                  <button className="link-button" type="button" onClick={() => navigate(`/recipes/${recipe.id}`)}>
                    {recipe.title}
                  </button>
                  <br />
                  <span className="hint">Page {recipe.page_number}</span>
                </li>
              ))}
            </ul>
          )}
        </section>
      )}

      <div className="actions">
        <button type="button" onClick={() => navigate("/books")}>
          Back To Books
        </button>
      </div>
    </>
  );
}

function RecipeDetailPage({ recipeId, navigate }) {
  const [recipe, setRecipe] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadRecipe() {
      setLoading(true);
      setError("");
      try {
        const response = await fetch(`/api/recipes/${recipeId}`);
        if (!response.ok) throw new Error(`Failed to load recipe: ${response.status}`);
        const data = await response.json();
        setRecipe(data.recipe ?? null);
      } catch (err) {
        setError(err.message || "Failed to load recipe.");
      } finally {
        setLoading(false);
      }
    }
    loadRecipe();
  }, [recipeId]);

  return (
    <>
      <h1>Recipe Detail</h1>
      {loading && <p className="hint">Loading recipe...</p>}
      {error && <p className="error">{error}</p>}

      {recipe && (
        <section className="uploaded-files">
          <h2>{recipe.title}</h2>
          <p className="hint">
            <strong>Book:</strong> {recipe.book_name}
            <br />
            <strong>Page:</strong> {recipe.page_number}
          </p>

          <h3>Ingredients</h3>
          {recipe.ingredients?.length > 0 ? (
            <ul>
              {recipe.ingredients.map((ingredient, idx) => (
                <li key={`${idx}-${ingredient}`}>{ingredient}</li>
              ))}
            </ul>
          ) : (
            <p className="hint">No ingredient lines were captured.</p>
          )}
        </section>
      )}

      <div className="actions">
        <button type="button" onClick={() => navigate("/recipes")}>
          Back To Recipes
        </button>
      </div>
    </>
  );
}

export default function App() {
  const { pathname, navigate } = usePathname();
  const recipeMatch = pathname.match(/^\/recipes\/(\d+)$/);
  const bookMatch = pathname.match(/^\/books\/(\d+)$/);

  return (
    <main className="app">
      <nav className="top-nav">
        <button type="button" className={pathname === "/" ? "nav-active" : ""} onClick={() => navigate("/")}>
          Uploads
        </button>
        <button
          type="button"
          className={pathname.startsWith("/recipes") ? "nav-active" : ""}
          onClick={() => navigate("/recipes")}
        >
          Recipes
        </button>
        <button
          type="button"
          className={pathname.startsWith("/books") ? "nav-active" : ""}
          onClick={() => navigate("/books")}
        >
          Books
        </button>
      </nav>

      {recipeMatch ? (
        <RecipeDetailPage recipeId={recipeMatch[1]} navigate={navigate} />
      ) : bookMatch ? (
        <BookDetailPage uploadId={bookMatch[1]} navigate={navigate} />
      ) : pathname.startsWith("/books") ? (
        <BooksPage navigate={navigate} />
      ) : pathname.startsWith("/recipes") ? (
        <RecipesPage navigate={navigate} />
      ) : (
        <UploadsPage navigate={navigate} />
      )}
    </main>
  );
}
