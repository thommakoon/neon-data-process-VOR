% launchAnalysisWindow.m
%
% Interactive selection tool for VVOR analysis.
% Allows the user to visually select a time window on the head/eye velocity plot,
% and pass the selected data to analizeVOR.
% Compatible with Octave 10+ and MATLAB.

function launchAnalysisWindow(t, e, h, s)
    % Default analysis window: full range
    tmin = t(1);
    tmax = t(end);

    % Create wider figure window
    f = figure('Name', 'VVOR Analysis Window Selector', ...
               'NumberTitle', 'off', ...
               'Position', [100 100 1000 500]);

    % Plot head and eye velocities
    plot(t, e, 'b', t, h, 'r');
    legend('Head velocity (h)', 'Eye velocity (e)');
    xlabel('Time (s)');
    ylabel('Velocity');
    title('Select analysis window (click to update markers, then press Analyze)');
    ylim([-300 300]);

    % Draw initial window markers and labels
    hold on;
    leftMarker = xline(tmin, 'k--', 'Left', 'LabelOrientation', 'horizontal', 'LineWidth', 2);
    rightMarker = xline(tmax, 'k--', 'Right', 'LabelOrientation', 'horizontal', 'LineWidth', 2);
    dtLabel = text(mean([tmin tmax]), 280, ...
        sprintf('\\Deltat = %.3f s', tmax - tmin), ...
        'HorizontalAlignment', 'center', 'FontWeight', 'bold');
    rangeLabel = text(mean([tmin tmax]), 260, ...
        sprintf('Start: %.3f s   End: %.3f s', tmin, tmax), ...
        'HorizontalAlignment', 'center', 'FontAngle', 'italic');
    hold off;

    % Button to reselect window
    uicontrol('Style', 'pushbutton', 'String', 'Select Window', ...
        'Position', [20 20 100 30], ...
        'Callback', @(src, event) selectWindow());

    % Button to run analysis
    uicontrol('Style', 'pushbutton', 'String', 'Analyze', ...
        'Position', [140 20 100 30], ...
        'Callback', @(src, event) analyzeCurrentWindow());

    % Shared variables and nested logic
    function selectWindow()
        disp('Click two points on the plot to set window...');
        [x, ~] = ginput(2);
        tmin = min(x);
        tmax = max(x);
        leftMarker.Value = tmin;
        rightMarker.Value = tmax;
        dt = tmax - tmin;
        dtLabel.Position = [mean([tmin tmax]), 280];
        dtLabel.String = sprintf('\\Deltat = %.3f s', dt);
        rangeLabel.Position = [mean([tmin tmax]), 260];
        rangeLabel.String = sprintf('Start: %.3f s   End: %.3f s', tmin, tmax);
    end

    function analyzeCurrentWindow()
        idx = (t >= tmin) & (t <= tmax);
        if sum(idx) < 2
            warndlg('Selected window is too narrow.', 'Warning');
            return;
        end
        analizeVOR(t(idx), e(idx), h(idx), s);
    end
end