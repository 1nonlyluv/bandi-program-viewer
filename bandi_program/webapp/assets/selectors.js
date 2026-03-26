(function () {
  "use strict";

  function parseClockToMinutes(value) {
    if (!value || typeof value !== "string") {
      return null;
    }
    var match = /^(\d{1,2}):(\d{2})$/.exec(value.trim());
    if (!match) {
      return null;
    }
    return Number(match[1]) * 60 + Number(match[2]);
  }

  function pad2(value) {
    return String(value).padStart(2, "0");
  }

  function parseAtString(at) {
    if (!at || typeof at !== "string") {
      return null;
    }
    var match = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/.exec(at.trim());
    if (!match) {
      return null;
    }
    return {
      date: [match[1], match[2], match[3]].join("-"),
      minutes: Number(match[4]) * 60 + Number(match[5]),
      hour: Number(match[4]),
      minute: Number(match[5])
    };
  }

  function getNowParts(timezone) {
    var formatter = new Intl.DateTimeFormat("ko-KR", {
      timeZone: timezone || "Asia/Seoul",
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false
    });
    var parts = formatter.formatToParts(new Date());
    var map = {};
    parts.forEach(function (part) {
      if (part.type !== "literal") {
        map[part.type] = part.value;
      }
    });
    return {
      date: [map.year, map.month, map.day].join("-"),
      minutes: Number(map.hour) * 60 + Number(map.minute),
      hour: Number(map.hour),
      minute: Number(map.minute)
    };
  }

  function resolveAtParts(at, timezone) {
    return parseAtString(at) || getNowParts(timezone);
  }

  function sortBlocks(blocks) {
    return (blocks || []).slice().sort(function (a, b) {
      return (a.startMin || 0) - (b.startMin || 0);
    });
  }

  function selectDay(data, date) {
    if (!data || !Array.isArray(data.days)) {
      return null;
    }
    return data.days.find(function (day) {
      return day.date === date;
    }) || null;
  }

  function selectPrevNextBlocks(day, nowMinutes) {
    var blocks = sortBlocks(day && day.blocks);
    var prevBlock = null;
    var nextBlock = null;

    blocks.forEach(function (block) {
      if ((block.endMin || 0) <= nowMinutes) {
        prevBlock = block;
      }
      if (!nextBlock && (block.startMin || 0) > nowMinutes) {
        nextBlock = block;
      }
    });

    return {
      prevBlock: prevBlock,
      nextBlock: nextBlock
    };
  }

  function matchesList(valueList, filterList) {
    if (!Array.isArray(filterList) || filterList.length === 0) {
      return true;
    }
    if (!Array.isArray(valueList)) {
      return false;
    }
    return valueList.some(function (value) {
      return filterList.indexOf(value) !== -1;
    });
  }

  function includesQuery(entry, query) {
    if (!query) {
      return true;
    }
    var lower = String(query).trim().toLowerCase();
    if (!lower) {
      return true;
    }
    var haystack = [
      entry.title,
      entry.subtitle,
      entry.location,
      entry.staffRole
    ]
      .concat(entry.staff || [])
      .concat(entry.tags || [])
      .join(" ")
      .toLowerCase();
    return haystack.indexOf(lower) !== -1;
  }

  function matchesFilters(entry, filters) {
    var safeFilters = filters || {};
    if (!matchesList(entry.groupIds || [], safeFilters.groups || [])) {
      return false;
    }
    if (
      Array.isArray(safeFilters.categories) &&
      safeFilters.categories.length > 0 &&
      safeFilters.categories.indexOf(entry.categoryId) === -1
    ) {
      return false;
    }
    if (!matchesList(entry.staff || [], safeFilters.staff || [])) {
      return false;
    }
    if (!includesQuery(entry, safeFilters.query || "")) {
      return false;
    }
    return true;
  }

  function selectVisibleEntries(block, filters) {
    if (!block || !Array.isArray(block.entries)) {
      return [];
    }
    return block.entries.filter(function (entry) {
      return matchesFilters(entry, filters);
    });
  }

  function buildStatus(day, blocks, activeBlock, nowMinutes) {
    if (!day || blocks.length === 0) {
      return "no_data";
    }
    if (activeBlock) {
      return "in_block";
    }
    if (nowMinutes < (blocks[0].startMin || 0)) {
      return "before_open";
    }
    if (nowMinutes >= (blocks[blocks.length - 1].endMin || 0)) {
      return "after_close";
    }
    return "between_blocks";
  }

  function selectNowState(data, at, filters) {
    var timezone = data && data.meta && data.meta.timezone ? data.meta.timezone : "Asia/Seoul";
    var now = resolveAtParts(at, timezone);
    var day = selectDay(data, now.date);
    var blocks = sortBlocks(day && day.blocks);
    var activeBlock = blocks.find(function (block) {
      return (block.startMin || 0) <= now.minutes && now.minutes < (block.endMin || 0);
    }) || null;
    var around = selectPrevNextBlocks(day, now.minutes);
    var status = buildStatus(day, blocks, activeBlock, now.minutes);
    var remainingMinutes = activeBlock ? activeBlock.endMin - now.minutes : null;
    var upcomingMinutes = !activeBlock && around.nextBlock ? around.nextBlock.startMin - now.minutes : null;

    return {
      at: now,
      status: status,
      day: day,
      block: activeBlock,
      prevBlock: around.prevBlock,
      nextBlock: around.nextBlock,
      remainingMinutes: remainingMinutes,
      upcomingMinutes: upcomingMinutes,
      visibleEntries: selectVisibleEntries(activeBlock, filters)
    };
  }

  function selectTimeline(day) {
    return sortBlocks(day && day.blocks).map(function (block) {
      return {
        id: block.id,
        start: block.start,
        end: block.end,
        section: block.section,
        count: Array.isArray(block.entries) ? block.entries.length : 0
      };
    });
  }

  function flattenEntries(data) {
    if (!data || !Array.isArray(data.days)) {
      return [];
    }
    var entries = [];
    data.days.forEach(function (day) {
      (day.blocks || []).forEach(function (block) {
        (block.entries || []).forEach(function (entry) {
          entries.push({
            id: entry.id,
            date: day.date,
            weekday: day.weekday,
            start: block.start,
            end: block.end,
            startMin: block.startMin,
            endMin: block.endMin,
            section: block.section,
            title: entry.title,
            subtitle: entry.subtitle,
            categoryId: entry.categoryId,
            groupIds: entry.groupIds || [],
            staff: entry.staff || [],
            staffRole: entry.staffRole || "",
            location: entry.location || "",
            tags: entry.tags || []
          });
        });
      });
    });
    return entries;
  }

  function compareBrowseEntries(a, b, sort) {
    if (sort === "title") {
      return String(a.title).localeCompare(String(b.title), "ko");
    }
    if (sort === "group") {
      return String((a.groupIds || []).join(",")).localeCompare(String((b.groupIds || []).join(",")), "ko");
    }
    if (sort === "category") {
      return String(a.categoryId || "").localeCompare(String(b.categoryId || ""), "ko");
    }
    return String(a.date + "T" + a.start).localeCompare(String(b.date + "T" + b.start), "ko");
  }

  function selectBrowseEntries(data, filters, sort) {
    return flattenEntries(data)
      .filter(function (entry) {
        return matchesFilters(entry, filters);
      })
      .sort(function (a, b) {
        return compareBrowseEntries(a, b, sort || "time");
      });
  }

  window.ProgramViewerSelectors = {
    parseClockToMinutes: parseClockToMinutes,
    resolveAtParts: resolveAtParts,
    selectDay: selectDay,
    selectPrevNextBlocks: selectPrevNextBlocks,
    selectVisibleEntries: selectVisibleEntries,
    selectNowState: selectNowState,
    selectTimeline: selectTimeline,
    flattenEntries: flattenEntries,
    selectBrowseEntries: selectBrowseEntries
  };
})();
