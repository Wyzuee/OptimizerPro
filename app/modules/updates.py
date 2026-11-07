"""Windows Update tarama ve kurulum (Microsoft.Update COM)."""
from __future__ import annotations

from dataclasses import dataclass

from ..core import logger, ps

SEARCH_SCRIPT = r"""
$ErrorActionPreference='Stop'
try {
  $session = New-Object -ComObject Microsoft.Update.Session
  $searcher = $session.CreateUpdateSearcher()
  $searcher.Online = $false
  $result = $searcher.Search("IsInstalled=0 and IsHidden=0")
  $items = @()
  $i = 0
  foreach ($u in $result.Updates) {
    $items += [pscustomobject]@{
      index     = $i
      title     = $u.Title
      kb        = (@($u.KBArticleIDs) -join ', ')
      driver    = [bool]$u.IsDriver
      size      = [long]$u.MaxDownloadSize
      mandatory = [bool]$u.IsMandatory
      reboot    = [bool]$u.InstallationBehavior.RebootBehavior
    }
    $i++
  }
  [pscustomobject]@{ ok=$true; updates=$items; count=$result.Updates.Count } | ConvertTo-Json -Compress -Depth 4
} catch {
  [pscustomobject]@{ ok=$false; error=$_.Exception.Message; updates=@(); count=0 } | ConvertTo-Json -Compress -Depth 4
}
"""

INSTALL_SCRIPT = r"""
$ErrorActionPreference='Stop'
$indices = @(%s)
try {
  $session = New-Object -ComObject Microsoft.Update.Session
  $searcher = $session.CreateUpdateSearcher()
  $searcher.Online = $false
  $result = $searcher.Search("IsInstalled=0 and IsHidden=0")
  $coll = New-Object -ComObject Microsoft.Update.UpdateColl
  $i = 0
  foreach ($u in $result.Updates) {
    if ($indices -contains $i) {
      if (-not $u.EulaAccepted) { $u.AcceptEula() }
      $coll.Add($u) | Out-Null
      Write-Output ("SEÇİLDİ: " + $u.Title)
    }
    $i++
  }
  if ($coll.Count -eq 0) { Write-Output "Kurulacak güncelleme bulunamadı."; exit 0 }
  $downloader = $session.CreateUpdateDownloader()
  $downloader.Updates = $coll
  Write-Output "İndiriliyor..."
  $null = $downloader.Download()
  $installer = $session.CreateUpdateInstaller()
  $installer.Updates = $coll
  Write-Output "Kuruluyor..."
  $installResult = $installer.Install()
  Write-Output ("SONUÇ: " + $installResult.ResultCode + " / yeniden başlatma gerekli: " + $installResult.RebootRequired)
} catch {
  Write-Output ("HATA: " + $_.Exception.Message)
}
"""


@dataclass
class UpdateInfo:
    index: int
    title: str
    kb: str
    is_driver: bool
    size: int
    mandatory: bool

    @property
    def size_h(self) -> str:
        from ..core.download import human_size
        return human_size(self.size) if self.size else "—"

    @property
    def kind(self) -> str:
        return "Sürücü" if self.is_driver else "Güncelleme"


def search(dry_run: bool = False) -> tuple[list[UpdateInfo], str]:
    """(güncellemeler, hata_mesajı)"""
    if dry_run:
        logger.info("[DRY-RUN] Windows Update taraması")
        return [], ""

    data = ps.ps_json(SEARCH_SCRIPT, timeout=600, default={}) or {}
    if not data.get("ok"):
        message = str(data.get("error") or "Bilinmeyen hata")
        logger.warn(f"Windows Update taraması başarısız: {message}")
        return [], message

    items = data.get("updates") or []
    if isinstance(items, dict):
        items = [items]

    updates = []
    for row in items:
        if not isinstance(row, dict):
            continue
        updates.append(UpdateInfo(
            index=int(row.get("index") or 0),
            title=str(row.get("title") or ""),
            kb=str(row.get("kb") or ""),
            is_driver=bool(row.get("driver")),
            size=int(row.get("size") or 0),
            mandatory=bool(row.get("mandatory")),
        ))
    logger.info(f"{len(updates)} güncelleme bulundu")
    return updates, ""


def install(indices: list[int], dry_run: bool = False, on_line=None, timeout: float = 7200) -> tuple[bool, str]:
    if not indices:
        return True, "seçim yok"
    if dry_run:
        logger.info(f"[DRY-RUN] Güncellemeler kurulacak: {indices}")
        return True, "dry-run"

    script = INSTALL_SCRIPT % ",".join(str(int(i)) for i in indices)
    result = ps.run_powershell(script, on_line=on_line, timeout=timeout, label="Windows Update kurulumu")
    ok = result.ok and "HATA:" not in (result.output or "")
    return ok, result.output[-400:] if result.output else ""
