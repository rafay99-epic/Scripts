
# Define the paths to your Flutter SDKs
$flutterSDKs = @{
    "3.16.9" = "D:\Flutter Archieve\Version 3.16\flutter"
    "3.19.2" = "D:\Flutter Archieve\Version 3.19\flutter"
    "3.3.0"  = "D:\Flutter Archieve\Version-3.3.0\flutter"
}
try {
    Write-Host""
    Write-Host""
    
    Write-Host @"
    ███████╗██╗     ██╗   ██╗████████╗████████╗███████╗██████╗     ███████╗██╗    ██╗██╗████████╗ ██████╗██╗  ██╗    ███████╗ ██████╗██████╗ ██╗██████╗ ████████╗
    ██╔════╝██║     ██║   ██║╚══██╔══╝╚══██╔══╝██╔════╝██╔══██╗    ██╔════╝██║    ██║██║╚══██╔══╝██╔════╝██║  ██║    ██╔════╝██╔════╝██╔══██╗██║██╔══██╗╚══██╔══╝
    █████╗  ██║     ██║   ██║   ██║      ██║   █████╗  ██████╔╝    ███████╗██║ █╗ ██║██║   ██║   ██║     ███████║    ███████╗██║     ██████╔╝██║██████╔╝   ██║   
    ██╔══╝  ██║     ██║   ██║   ██║      ██║   ██╔══╝  ██╔══██╗    ╚════██║██║███╗██║██║   ██║   ██║     ██╔══██║    ╚════██║██║     ██╔══██╗██║██╔═══╝    ██║   
    ██║     ███████╗╚██████╔╝   ██║      ██║   ███████╗██║  ██║    ███████║╚███╔███╔╝██║   ██║   ╚██████╗██║  ██║    ███████║╚██████╗██║  ██║██║██║        ██║   
    ╚═╝     ╚══════╝ ╚═════╝    ╚═╝      ╚═╝   ╚══════╝╚═╝  ╚═╝    ╚══════╝ ╚══╝╚══╝ ╚═╝   ╚═╝    ╚═════╝╚═╝  ╚═╝    ╚══════╝ ╚═════╝╚═╝  ╚═╝╚═╝╚═╝        ╚═╝   
"@
    Write-Host "This script will switch between different versions of Flutter SDKs."
    Write-Host""
    # Ask the user which version they want to switch to
    $version = Read-Host -Prompt 'Input the Flutter version you want to switch to (3.16.9, 3.19.2, 3.3.0)'

    # Check if the version exists in the defined paths
    if ($flutterSDKs.ContainsKey($version)) {
        # Check if Flutter is currently running
        $flutterProcess = Get-Process | Where-Object { $_.Path -like "*flutter*" }

        # If Flutter is running, kill the process
        if ($null -ne $flutterProcess) {
            Stop-Process -Name $flutterProcess.Name -Force
        }

        # Check if there is a Flutter folder in the D:\ directory
        if (Test-Path -Path "D:\flutter") {
            # Get the Flutter version in the D:\flutter directory
            $currentVersionOutput = & "D:\flutter\bin\flutter.bat" --version
            $currentVersion = $currentVersionOutput.Split(' ')[1]

            # Move the current Flutter folder to its corresponding location
            if ($flutterSDKs.ContainsKey($currentVersion)) {
                Move-Item -Path "D:\flutter" -Destination $flutterSDKs[$currentVersion]
            }
        }

        # Check if the chosen Flutter version exists
        if (Test-Path -Path $flutterSDKs[$version]) {
            # Move the chosen Flutter version to the D:\ directory
            Move-Item -Path $flutterSDKs[$version] -Destination "D:\flutter"

            Write-Host "Switched to Flutter $version version"
        }
        else {
            Write-Host "The Flutter version you chose does not exist at the specified path."
        }
    }
    else {
        Write-Host "The version you entered does not exist. Please enter either '3.16.9', '3.19.2', or '3.3.0'."
    }
}
catch {
    Write-Host "An error occurred: $_"
    Write-Host "Please try again."
}