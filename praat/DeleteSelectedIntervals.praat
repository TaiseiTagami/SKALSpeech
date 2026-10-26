# Delete intervals overlapping the selected time range on the selected tier.
# Run from a TextGrid editor with a time range selected.
editor: "TextGrid"
    tier = Get selected tier
    startTime = Get start of selection
    endTime = Get end of selection
    if endTime <= startTime
        exitScript: "Select a time range spanning the intervals to delete."
    endif
    n = Get number of intervals: tier
    for i from n to 1
        left = Get starting point: tier, i
        right = Get end point: tier, i
        if left < endTime and right > startTime
            if i > 1
                Remove left boundary: tier, i
            elsif i < n
                Remove right boundary: tier, i
            else
                Set interval text: tier, i, ""
            endif
        endif
    endfor
endeditor
