Set WshShell = CreateObject("WScript.Shell")
Set Fso = CreateObject("Scripting.FileSystemObject")
WshShell.CurrentDirectory = Fso.GetParentFolderName(WScript.ScriptFullName)

agentArg = ""
If WScript.Arguments.Count > 0 Then
  agentArg = " " & WScript.Arguments(0)
End If

exitCode = WshShell.Run("cmd /c Install.bat" & agentArg, 1, True)
If exitCode = 0 Then
  MsgBox "SkillPointer installed successfully!", vbInformation, "Installation Complete"
End If
