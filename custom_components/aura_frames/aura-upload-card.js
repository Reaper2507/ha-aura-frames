class AuraUploadCard extends HTMLElement {
  setConfig(config) {
    if (!Array.isArray(config.frames) || !config.frames.length) {
      throw new Error("Aura Upload: frames fehlen");
    }
    this._config = config;
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
  }

  getCardSize() { return 5; }

  _render() {
    const root = this.shadowRoot;
    root.innerHTML = `<style>
      ha-card { padding: 20px; }
      h2 { margin: 0 0 8px; font-size: 22px; }
      p { margin: 0 0 18px; opacity: .75; }
      .grid { display: grid; gap: 16px; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); }
      label { display: grid; gap: 7px; font-weight: 600; }
      input, select, button { font: inherit; box-sizing: border-box; width: 100%; min-height: 46px; }
      input, select { padding: 10px; border: 1px solid var(--divider-color); border-radius: 10px; color: var(--primary-text-color); background: var(--card-background-color); }
      .actions { margin-top: 16px; display: flex; align-items: center; gap: 16px; flex-wrap: wrap; }
      button { width: auto; min-width: 220px; padding: 10px 18px; border: 0; border-radius: 11px; color: var(--text-primary-color, white); background: var(--primary-color); cursor: pointer; font-weight: 700; }
      button:disabled { opacity: .5; cursor: wait; }
      #status { flex: 1; min-width: 200px; }
      #preview { display: none; max-width: 240px; max-height: 180px; margin-top: 16px; border-radius: 10px; object-fit: contain; }
    </style><ha-card><h2>Foto an Aura-Rahmen senden</h2>
      <p>Bild auswählen, Zielrahmen festlegen und sofort anzeigen.</p>
      <div class="grid"><label>Foto<input id="file" type="file" accept="image/*"></label>
      <label>Zielrahmen<select id="frame"></select></label></div>
      <img id="preview" alt="Vorschau des gewählten Bildes">
      <div class="actions"><button id="upload" type="button">Hochladen und anzeigen</button>
      <span id="status" role="status" aria-live="polite"></span></div></ha-card>`;
    const select = root.getElementById("frame");
    for (const frame of this._config.frames) {
      const option = document.createElement("option");
      option.value = frame.id;
      option.textContent = frame.name;
      select.append(option);
    }
    root.getElementById("file").addEventListener("change", event => {
      if (this._previewUrl) URL.revokeObjectURL(this._previewUrl);
      const file = event.target.files[0];
      const preview = root.getElementById("preview");
      if (file) {
        this._previewUrl = URL.createObjectURL(file);
        preview.src = this._previewUrl;
        preview.style.display = "block";
      } else {
        preview.removeAttribute("src");
        preview.style.display = "none";
      }
      root.getElementById("status").textContent = "";
    });
    root.getElementById("upload").addEventListener("click", () => this._upload());
  }

  async _upload() {
    const root = this.shadowRoot;
    const file = root.getElementById("file").files[0];
    const frameId = root.getElementById("frame").value;
    const status = root.getElementById("status");
    if (!file || !frameId) {
      status.textContent = "Bitte zuerst Foto und Zielrahmen auswählen.";
      return;
    }
    const button = root.getElementById("upload");
    button.disabled = true;
    status.textContent = "Bild wird hochgeladen …";
    try {
      const bitmap = await createImageBitmap(file);
      const scale = Math.min(1, 2000 / Math.max(bitmap.width, bitmap.height));
      const canvas = document.createElement("canvas");
      canvas.width = Math.max(1, Math.round(bitmap.width * scale));
      canvas.height = Math.max(1, Math.round(bitmap.height * scale));
      canvas.getContext("2d").drawImage(bitmap, 0, 0, canvas.width, canvas.height);
      bitmap.close();
      const jpeg = await new Promise(resolve => canvas.toBlob(resolve, "image/jpeg", .88));
      if (!jpeg || jpeg.size > 8 * 1024 * 1024) throw new Error("Bild konnte nicht auf unter 8 MB verarbeitet werden.");
      const content = await new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(String(reader.result).split(",", 2)[1]);
        reader.onerror = () => reject(new Error("Bilddatei konnte nicht gelesen werden."));
        reader.readAsDataURL(jpeg);
      });
      await this._hass.callWS({ type: "aura_frames/upload", frame_id: frameId, content });
      status.textContent = "Hochgeladen und Anzeige am Rahmen angefordert.";
    } catch (error) {
      status.textContent = `Upload fehlgeschlagen: ${error.message || error}`;
    } finally {
      button.disabled = false;
    }
  }

  disconnectedCallback() {
    if (this._previewUrl) URL.revokeObjectURL(this._previewUrl);
  }
}

if (!customElements.get("aura-upload-card")) {
  customElements.define("aura-upload-card", AuraUploadCard);
}
window.customCards = window.customCards || [];
window.customCards.push({ type: "aura-upload-card", name: "Aura Foto-Upload", description: "Bild auswählen und an einen Aura-Rahmen senden" });
