param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$Repository,

    [Parameter(Position = 1)]
    [string]$SkillName,

    [Parameter(Position = 2)]
    [string]$TargetSkillsDir = ".agents/skills",

    [Parameter(Position = 3)]
    [string]$Ref,

    [switch]$All
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Fail {
    param([string]$Message)
    Write-Error $Message
    exit 1
}

function Parse-Repo {
    param([string]$InputRepo)

    $clean = $InputRepo.Trim()
    $clean = $clean -replace "^https?://github\.com/", ""
    $clean = $clean.TrimStart('/')
    $clean = $clean.TrimEnd('/')

    if ($clean -notmatch "^[^/]+/[^/]+$") {
        Fail "Repository must be '/owner/repo', 'owner/repo', or a GitHub repo URL."
    }

    $parts = $clean.Split('/')
    return @{ owner = $parts[0]; repo = $parts[1] }
}

function Resolve-Tree {
    param(
        [string]$Owner,
        [string]$Repo,
        [string[]]$Refs,
        [hashtable]$Headers
    )

    foreach ($candidate in $Refs) {
        $treeUrl = "https://api.github.com/repos/$Owner/$Repo/git/trees/${candidate}?recursive=1"
        try {
            $result = Invoke-RestMethod -Method Get -Uri $treeUrl -Headers $Headers
            if ($result.tree) {
                return @{ ref = $candidate; tree = $result.tree }
            }
        }
        catch {
            # Try the next ref if this one does not exist.
            continue
        }
    }

    return $null
}

function Find-SkillPath {
    param(
        [object[]]$Tree,
        [string]$Skill
    )

    $escapedSkill = [Regex]::Escape($Skill)
    $matches = @($Tree | Where-Object {
        $_.type -eq "blob" -and
        $_.path -match "SKILL\.md$" -and
        $_.path -match "(^|/)$escapedSkill/SKILL\.md$"
    })

    if (-not $matches -or $matches.Count -eq 0) {
        return $null
    }

    $ranked = $matches | Sort-Object `
        @{ Expression = {
                if ($_.path -eq "skills/$Skill/SKILL.md") { 0 }
                elseif ($_.path -like "plugins/*/skills/$Skill/SKILL.md") { 1 }
                else { 2 }
            }
        }, `
        @{ Expression = { $_.path.Length } }

    return $ranked[0].path
}

function Get-SkillNameFromPath {
    param([string]$SkillPath)

    $parentPath = Split-Path -Path $SkillPath -Parent
    return Split-Path -Path $parentPath -Leaf
}

function Select-BestSkillPaths {
    param([object[]]$SkillBlobs)

    $grouped = $SkillBlobs | Group-Object { Get-SkillNameFromPath -SkillPath $_.path }
    $selected = @()

    foreach ($group in $grouped) {
        $skill = $group.Name
        $ranked = $group.Group | Sort-Object `
            @{ Expression = {
                    if ($_.path -eq "skills/$skill/SKILL.md") { 0 }
                    elseif ($_.path -like "plugins/*/skills/$skill/SKILL.md") { 1 }
                    else { 2 }
                }
            }, `
            @{ Expression = { $_.path.Length } }

        $selected += [PSCustomObject]@{
            SkillName = $skill
            SkillPath = $ranked[0].path
        }
    }

    return @($selected | Sort-Object SkillName)
}

function Install-SkillFiles {
    param(
        [string]$Owner,
        [string]$Repo,
        [string]$BranchRef,
        [object[]]$Tree,
        [string]$ResolvedSkillName,
        [string]$ResolvedSkillPath,
        [string]$BaseTargetSkillsDir,
        [hashtable]$Headers
    )

    $skillRootPath = Split-Path -Path $ResolvedSkillPath -Parent
    $skillRootPrefix = "$skillRootPath/"

    $skillFiles = @($Tree | Where-Object {
        $_.type -eq "blob" -and
        ($_.path -eq $ResolvedSkillPath -or $_.path.StartsWith($skillRootPrefix))
    })

    if ($skillFiles.Count -eq 0) {
        Fail "No files found for skill '$ResolvedSkillName' in '$Owner/$Repo'."
    }

    $destinationRoot = Join-Path $BaseTargetSkillsDir $ResolvedSkillName
    New-Item -ItemType Directory -Path $destinationRoot -Force | Out-Null

    $writtenFiles = 0
    $writtenBytes = 0

    foreach ($file in $skillFiles) {
        $relativePath = ""
        if ($file.path -eq $ResolvedSkillPath) {
            $relativePath = "SKILL.md"
        }
        else {
            $relativePath = $file.path.Substring($skillRootPath.Length + 1)
        }

        if ($relativePath.Contains("..")) {
            Fail "Unsafe file path '$relativePath' for skill '$ResolvedSkillName'."
        }

        $relativePathForOs = $relativePath -replace "/", [IO.Path]::DirectorySeparatorChar
        $destinationFile = Join-Path $destinationRoot $relativePathForOs
        $destinationDir = Split-Path -Path $destinationFile -Parent
        New-Item -ItemType Directory -Path $destinationDir -Force | Out-Null

        $rawUrl = "https://raw.githubusercontent.com/$Owner/$Repo/$BranchRef/$($file.path)"
        Invoke-WebRequest -UseBasicParsing -Uri $rawUrl -OutFile $destinationFile -Headers $Headers

        $writtenFiles += 1
        $writtenBytes += (Get-Item $destinationFile).Length
    }

    return [PSCustomObject]@{
        SkillName = $ResolvedSkillName
        SkillPath = $ResolvedSkillPath
        FileCount = $writtenFiles
        TotalBytes = $writtenBytes
    }
}

if (-not $All -and [string]::IsNullOrWhiteSpace($SkillName)) {
    Fail "Specify a skill name or pass -All to install every skill in the repository."
}

$repoInfo = Parse-Repo -InputRepo $Repository
$owner = $repoInfo.owner
$repo = $repoInfo.repo

$refsToTry = @()
if (-not [string]::IsNullOrWhiteSpace($Ref)) {
    $refsToTry += $Ref
}
$refsToTry += "master", "main"
$refsToTry = $refsToTry | Select-Object -Unique

$headers = @{
    "User-Agent" = "ctx7-skill-workaround"
    "Accept"     = "application/vnd.github+json"
}

$resolved = Resolve-Tree -Owner $owner -Repo $repo -Refs $refsToTry -Headers $headers
if (-not $resolved) {
    Fail "Could not read repo tree for '$owner/$repo' using refs: $($refsToTry -join ', ')."
}

$selectedRef = $resolved.ref
$tree = $resolved.tree

$allSkillBlobs = @($tree | Where-Object {
    $_.type -eq "blob" -and $_.path -match "(^|/)SKILL\.md$"
})

if ($allSkillBlobs.Count -eq 0) {
    Fail "No SKILL.md files were found in '$owner/$repo'."
}

$skillsToInstall = @()

if ($All) {
    $skillsToInstall = Select-BestSkillPaths -SkillBlobs $allSkillBlobs
}
else {
    $skillPath = Find-SkillPath -Tree $tree -Skill $SkillName
    if (-not $skillPath) {
        Fail "Could not locate SKILL.md for skill '$SkillName' in '$owner/$repo'."
    }

    $skillsToInstall = @([PSCustomObject]@{
        SkillName = $SkillName
        SkillPath = $skillPath
    })
}

$installed = @()

foreach ($skill in $skillsToInstall) {
    $result = Install-SkillFiles `
        -Owner $owner `
        -Repo $repo `
        -BranchRef $selectedRef `
        -Tree $tree `
        -ResolvedSkillName $skill.SkillName `
        -ResolvedSkillPath $skill.SkillPath `
        -BaseTargetSkillsDir $TargetSkillsDir `
        -Headers $headers

    $installed += $result
    Write-Host "Installed skill '$($result.SkillName)' ($($result.FileCount) file(s), $($result.TotalBytes) bytes)."
}

$installedCount = $installed.Count
$totalFiles = ($installed | Measure-Object -Property FileCount -Sum).Sum
$totalBytes = ($installed | Measure-Object -Property TotalBytes -Sum).Sum

Write-Host "Completed installation from '$owner/$repo' (ref '$selectedRef')."
Write-Host "Skills: $installedCount | Files: $totalFiles | Bytes: $totalBytes"

if ($All) {
    Write-Host "Installed skills: $($installed.SkillName -join ', ')"
}

