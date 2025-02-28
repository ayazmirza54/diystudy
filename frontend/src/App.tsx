import React, { useState } from 'react';

function App() {
  const [projectName, setProjectName] = useState('');
  const [githubUrl, setGithubUrl] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [response, setResponse] = useState<{
    success?: boolean;
    message?: string;
    error?: string;
    deployment_url?: string;
  } | null>(null);

  const handleSubmit = async () => {
    if (!githubUrl) {
      setResponse({ success: false, error: 'GitHub URL is required' });
      return;
    }

    if (!projectName) {
      setResponse({ success: false, error: 'Project name is required' });
      return;
    }

    setIsLoading(true);
    setResponse(null);

    try {
      const backendUrl = 'http://localhost:5000/api/clone-and-deploy';

      const response = await fetch(backendUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          github_url: githubUrl,
          project_name: projectName
        }),
      });

      const data = await response.json();

      if (response.ok) {
        setResponse({
          success: true,
          message: data.message,
          deployment_url: data.deployment_url
        });
      } else {
        setResponse({ success: false, error: data.error });
      }
    } catch (error) {
      setResponse({
        success: false,
        error: error instanceof Error ? error.message : 'Failed to connect to server'
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#000000] text-white flex flex-col items-center" style={{ fontFamily: 'JetBrains Mono, monospace' }}>
      <link
        href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@100;200;300;400;500;600;700;800&display=swap"
        rel="stylesheet"
      />

      {/* Main Content */}
      <div className="flex-1 relative overflow-hidden w-full max-w-6xl">
        {/* Logo and Tagline */}
        <div className="relative z-10 pt-12 px-8 flex flex-col items-center h-full">
          <div className="flex items-center gap-4 mb-8">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 border-2 border-[#00FF00] flex items-center justify-center transform rotate-45">
                <div className="w-6 h-6 border-2 border-[#00FF00]"></div>
              </div>
              <div className="w-10 h-10 border-2 border-white flex items-center justify-center">
                <div className="w-6 h-6 border-2 border-white transform -rotate-45"></div>
              </div>
            </div>
            <div className="text-2xl font-light tracking-wide">Build it yourself</div>
          </div>

          {/* Main Text */}
          <div className="text-center my-16">
            <div className="text-[100px] font-bold leading-none bg-gradient-to-r from-[#00FF00] via-[#7FFF00] to-[#98FB98] text-transparent bg-clip-text bg-size-200 animate-gradient tracking-tight">
              vercel.diy
            </div>
            <div className="text-xl tracking-wider mt-2 font-light text-gray-400">
              DEPLOY YOUR CREATIVITY • BUILD YOUR VISION
            </div>
          </div>

          {/* Form Inputs */}
          <div className="relative mt-auto mb-6 w-full max-w-4xl mx-auto space-y-4">
            {/* Project Name Input */}
            <div className="w-full h-16 border border-[#333] hover:border-[#00FF00] transition-colors duration-300 rounded-lg flex items-center overflow-hidden bg-[#111]">
              <input
                type="text"
                placeholder="Enter your project name"
                value={projectName}
                onChange={(e) => setProjectName(e.target.value)}
                className="flex-1 bg-transparent border-none outline-none px-8 text-xl font-light tracking-wide placeholder:text-gray-600"
              />
            </div>

            {/* GitHub URL Input */}
            <div className="w-full h-16 border border-[#333] hover:border-[#00FF00] transition-colors duration-300 rounded-lg flex items-center overflow-hidden bg-[#111]">
              <input
                type="text"
                placeholder="Enter GitHub repository URL (e.g., https://github.com/username/repo)"
                value={githubUrl}
                onChange={(e) => setGithubUrl(e.target.value)}
                className="flex-1 bg-transparent border-none outline-none px-8 text-xl font-light tracking-wide placeholder:text-gray-600"
              />
              <button
                onClick={handleSubmit}
                disabled={isLoading}
                className="h-full px-8 bg-white text-black font-medium hover:bg-[#00FF00] transition-colors duration-300 tracking-wide disabled:bg-gray-500 disabled:cursor-not-allowed"
              >
                {isLoading ? 'DEPLOYING...' : 'DEPLOY'}
              </button>
            </div>

            {/* Response message */}
            {response && (
              <div className={`p-4 rounded-lg ${response.success ? 'bg-green-900/30 border border-green-500' : 'bg-red-900/30 border border-red-500'}`}>
                {response.success ? (
                  <div>
                    <p className="text-green-400">{response.message}</p>
                    {response.deployment_url && (
                      <p className="mt-2">
                        Your site will be available at:{' '}
                        <a
                          href={response.deployment_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-[#00FF00] hover:underline"
                        >
                          {response.deployment_url}
                        </a>
                        <br />
                        <span className="text-sm text-gray-400">
                          (Note: It may take a few minutes for the site to be deployed)
                        </span>
                      </p>
                    )}
                  </div>
                ) : (
                  <p className="text-red-400">Error: {response.error}</p>
                )}
              </div>
            )}
          </div>

          {/* Instructions */}
          <div className="w-full max-w-4xl mx-auto mb-12 p-4 bg-[#111] border border-[#333] rounded-lg">
            <h3 className="text-xl font-medium mb-2 text-[#00FF00]">How it works:</h3>
            <ol className="list-decimal pl-6 space-y-2 text-gray-300">
              <li>Enter a name for your project deployment</li>
              <li>Paste your GitHub repository URL
                <div className="mt-1 text-sm bg-black p-2 rounded border border-gray-700">
                  <span className="text-[#00FF00] font-medium">✓ Use repository URL:</span>
                  <div className="text-green-400 overflow-x-auto whitespace-nowrap my-1">
                    https://github.com/username/repo
                  </div>
                  <span className="text-red-400 font-medium">✗ Do NOT use file or directory URLs:</span>
                  <div className="text-red-300 overflow-x-auto whitespace-nowrap my-1">
                    https://github.com/username/repo/tree/main
                  </div>
                </div>
              </li>
              <li>Click DEPLOY to clone your repository and set up GitHub Pages</li>
              <li>Once deployed, your site will be available at <code className="bg-black text-[#00FF00] px-2 py-1 rounded">username.github.io/repo-name</code></li>
              <li>The deployment process may take a few minutes to complete</li>
            </ol>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;