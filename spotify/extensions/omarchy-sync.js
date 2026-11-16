// Omarchy Live Theme Synchronization Extension for Spotify (Spicetify)
// Automatically checks for theme palette changes every 1 second and hot-reloads
// colors, CSS variables, and stylesheets in the running Spotify window without interruption.

(function OmarchyThemeSync() {
    let lastCss = "";

    async function applyThemeUpdate() {
        try {
            const resp = await fetch("/colors.css?_t=" + Date.now(), { cache: "no-store" });
            if (!resp.ok) return;
            const css = await resp.text();

            if (lastCss === "") {
                lastCss = css;
                return;
            }

            if (css !== lastCss) {
                lastCss = css;
                console.log("[Omarchy] Live theme change detected! Applying new palette...");

                // Parse :root CSS variables from colors.css and apply directly to documentElement
                const varMatches = css.matchAll(/--([a-zA-Z0-9_-]+)\s*:\s*([^;]+);/g);
                for (const match of varMatches) {
                    const varName = "--" + match[1].trim();
                    const varVal = match[2].trim();
                    document.documentElement.style.setProperty(varName, varVal);
                }

                // Update <link class="userCSS"> stylesheets
                const links = document.querySelectorAll("link.userCSS");
                links.forEach(link => {
                    const originalHref = link.getAttribute("href").split("?")[0];
                    link.setAttribute("href", originalHref + "?_t=" + Date.now());
                });

                // Fetch and inject updated user.css into a dedicated style tag
                try {
                    const userCssResp = await fetch("/user.css?_t=" + Date.now(), { cache: "no-store" });
                    if (userCssResp.ok) {
                        const userCssText = await userCssResp.text();
                        let styleTag = document.getElementById("omarchy-live-usercss");
                        if (!styleTag) {
                            styleTag = document.createElement("style");
                            styleTag.id = "omarchy-live-usercss";
                            document.head.appendChild(styleTag);
                        }
                        styleTag.textContent = userCssText;
                    }
                } catch (err) {
                    console.error("[Omarchy] Failed to update user.css:", err);
                }
            }
        } catch (e) {
            // Silently ignore transient fetch errors
        }
    }

    // Check every 1000ms
    setInterval(applyThemeUpdate, 1000);
    applyThemeUpdate();
    console.log("[Omarchy] Live theme sync extension initialized.");
})();
