import React, { useEffect, useState } from "react";

function InstallAppButton() {
  const [installPrompt, setInstallPrompt] = useState(null);

  useEffect(() => {
    const handleInstallPrompt = (event) => {
      event.preventDefault();
      setInstallPrompt(event);
    };

    window.addEventListener("beforeinstallprompt", handleInstallPrompt);
    return () => window.removeEventListener("beforeinstallprompt", handleInstallPrompt);
  }, []);

  if (!installPrompt) return null;

  const install = async () => {
    installPrompt.prompt();
    await installPrompt.userChoice;
    setInstallPrompt(null);
  };

  return (
    <button type="button" title="Install AnkurAI" onClick={install} className="install-app-button theme-button-secondary touch-target whitespace-nowrap px-3 py-2 text-xs sm:px-4 sm:text-sm">
      Install App
    </button>
  );
}

export default InstallAppButton;
